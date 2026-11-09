# -*- coding: utf-8 -*-
"""校对 生成的日课 md 与 JSON 数据是否完全一致（词条/读音/选项/答案/编号）。"""
import json
import re
import sys

md_path = sys.argv[1]
lo = int(sys.argv[2])
hi = int(sys.argv[3])

data = {e["id"]: e for e in json.load(open("_build/vocab_1001_2000.json", encoding="utf-8"))}
md = open(md_path, encoding="utf-8").read()
lines = md.splitlines()

errs = []

# 1) 学习页词条：**1001 最高潮**　中文 / 读音行 / 日 / 例 / 译 五行齐全且与 JSON 一致
entry_re = re.compile(r"^\*\*(\d{4}) (.+?)\*\*　(.*)$")
read_re = re.compile(r"^　读音：(.*)$")
jp_re = re.compile(r"^　日：(.*)$")
ex_re = re.compile(r"^　例：(.*)$")
tr_re = re.compile(r"^　译：(.*)$")
seen = {}
n = 0
for i, line in enumerate(lines):
    m = entry_re.match(line)
    if not m:
        continue
    wid = int(m.group(1))
    if not (lo <= wid < hi):
        continue
    n += 1
    if wid in seen:
        errs.append(f"{wid} 重复出现")
    seen[wid] = True
    e = data.get(wid)
    if not e:
        errs.append(f"{wid} 数据里没有")
        continue
    if m.group(2) != e["word"]:
        errs.append(f"{wid} 词形不符：{m.group(2)} vs {e['word']}")
    if m.group(3) != e["cn"]:
        errs.append(f"{wid} 中文不符：{m.group(3)} vs {e['cn']}")
    for j, (rx, key) in enumerate([(read_re, "reading"), (jp_re, "jp"), (ex_re, "example"), (tr_re, "trans")], start=1):
        if i + j >= len(lines):
            errs.append(f"{wid} 行数不足")
            break
        mm = rx.match(lines[i + j])
        if not mm:
            errs.append(f"{wid} 缺 {key} 行")
        elif mm.group(1) != e[key]:
            errs.append(f"{wid} {key} 不符")

if n != hi - lo:
    errs.append(f"学习页词条数 {n}，应为 {hi - lo}")
missing = [i for i in range(lo, hi) if i not in seen]
if missing:
    errs.append(f"缺词条：{missing}")

# 2) 盲测：**1001**　题干 + 选项行
q_re = re.compile(r"^\*\*(\d{4})\*\*　(.*)$")
opt_re = re.compile(r"^　　A (.+?)　／　B (.+?)　→　我选：____$")
qids = []
for i, line in enumerate(lines):
    m = q_re.match(line)
    if not m:
        continue
    wid = int(m.group(1))
    if not (lo <= wid < hi):
        continue
    qids.append(wid)
    e = data[wid]
    if m.group(2) != e["quiz"]:
        errs.append(f"{wid} 题干不符")
    mm = opt_re.match(lines[i + 2]) if i + 2 < len(lines) else None
    if not mm:
        errs.append(f"{wid} 选项行格式不对")
    elif (mm.group(1), mm.group(2)) != (e["optA"], e["optB"]):
        errs.append(f"{wid} 选项不符")
if qids != list(range(lo, hi)):
    errs.append(f"盲测题号/顺序不对，实际 {len(qids)} 题")

# 3) 答案行：1001　词｜读音｜中文　→ **B**（正确 X／干扰 Y）
ans_re = re.compile(r"^(\d{4})　(.+?)｜(.+?)｜(.+?)　→ \*\*([AB])\*\*（正确 (.+?)／干扰 (.+?)）$")
aids = []
for line in lines:
    m = ans_re.match(line)
    if not m:
        continue
    wid = int(m.group(1))
    if not (lo <= wid < hi):
        continue
    aids.append(wid)
    e = data[wid]
    right = e["optA"] if e["ans"] == "A" else e["optB"]
    wrong = e["optB"] if e["ans"] == "A" else e["optA"]
    if (m.group(2), m.group(3), m.group(4)) != (e["word"], e["reading"], e["cn"]):
        errs.append(f"{wid} 答案行词/读音/中文不符")
    if (m.group(5), m.group(6), m.group(7)) != (e["ans"], right, wrong):
        errs.append(f"{wid} 答案字母或正确/干扰不符")
if aids != list(range(lo, hi)):
    errs.append(f"答案条数/顺序不对，实际 {len(aids)} 条")

# 4) 排版体检：不许留坏字符、不许空行三连、序号小节齐全
for bad in ["⾼", "⽇", "⼼", "⻓", "⻅", "⻋", "⻤", "____", "TODO"]:
    if bad == "____":
        continue
    if bad in md:
        errs.append(f"残留坏字符 {bad}")
for need in ["## 一、学习页", "## 二、2 选 1 盲测", "## 三、易混对速记", "## 四、错题回炉", "## 五、+1 / +3 / +7 复习排程"]:
    if need not in md:
        errs.append(f"缺小节 {need}")
# 每组 20 题后要有该组的折叠答案
groups = re.findall(r"### 第 (\d) 组（(\d+)–(\d+)）", md)
answers = re.findall(r"<summary>第 (\d) 组答案（(\d+)–(\d+)）</summary>", md)
if len(groups) != len(answers) or [g[:2] for g in groups] != [a[:2] for a in answers]:
    errs.append(f"分组/组答案不配对：{len(groups)} 组，{len(answers)} 个答案块")
for g, a in zip(groups, answers):
    if g[1:] != a[1:]:
        errs.append(f"第 {g[0]} 组范围不一致：{g[1:]} vs {a[1:]}")

print(f"学习页 {n} 词 / 盲测 {len(qids)} 题 / 答案 {len(aids)} 条")
print("问题：", len(errs))
for e in errs[:40]:
    print(" -", e)
