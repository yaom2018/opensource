# -*- coding: utf-8 -*-
"""Day11–Day20 总验收：编号连续性、题/答配对、答题卡、排程交叉引用、残留占位。

用法：python _build/final_qa.py
"""
import re

DAYS = range(11, 21)
all_ids = []


def check(day):
    p = f"10天背诵/Day{day:02d}.md"
    t = open(p, encoding="utf-8").read()
    lo = 1001 + (day - 11) * 100
    hi = lo + 99
    errs = []

    learn = [int(m.group(1)) for m in re.finditer(r"^\*\*(\d{4}) \S+\*\*　", t, flags=re.M)]
    quiz = [int(m.group(1)) for m in re.finditer(r"^\*\*(\d{4})\*\*　", t, flags=re.M)]
    ans = [int(m.group(1)) for m in re.finditer(r"^(\d{4})　[^\n]*?→\s*\*\*[AB]\*\*", t, flags=re.M)]
    card = len(re.findall(r"(?:^|\s)\d{2} __", t, flags=re.M))
    # 答题卡是 10 行 × 10 组
    card_block = re.search(r"\*\*答题卡.*?```text\n(.*?)\n```", t, re.S)
    card_cells = len(re.findall(r"\d{1,3} __", card_block.group(1))) if card_block else 0

    for name, ids in (("学习页", learn), ("题目", quiz), ("答案", ans)):
        if len(ids) != 100:
            errs.append(f"{name} {len(ids)} 条（应 100）")
        if ids != list(range(lo, hi + 1)):
            bad = [i for i in ids if not (lo <= i <= hi)]
            dup = {i for i in ids if ids.count(i) > 1}
            errs.append(f"{name} 编号不连续/越界/重复：越界{bad[:5]} 重复{sorted(dup)[:5]}")
    if card_cells != 100:
        errs.append(f"答题卡 {card_cells} 格（应 100）")

    # 5 组 × 20 题 + 每组答案块
    groups = re.findall(r"^### 第 (\d) 组（(\d{4})–(\d{4})）", t, flags=re.M)
    keys = re.findall(r"<summary>第 (\d) 组答案（(\d{4})–(\d{4})）</summary>", t, flags=re.M)
    if [g[0] for g in groups] != ["1", "2", "3", "4", "5"]:
        errs.append(f"分组标题异常：{len(groups)} 组")
    if [g[0] for g in groups] != [k[0] for k in keys]:
        errs.append("答案块与题目分组不配对")
    for g, k in zip(groups, keys):
        if g[1:] != k[1:]:
            errs.append(f"第{g[0]}组区间不一致：{g[1:]} vs {k[1:]}")

    # 排程交叉引用
    for off in (1, 3, 7):
        want = f"+{off} → Day {day + off}"
        if day + off <= 27 and want not in t:
            errs.append(f"排程缺「{want}」")

    if "PLACEHOLDER" in t or "<!--" in t:
        errs.append("残留占位注释")
    if re.search(r"[ \t]1{1,3}$", t, flags=re.M):
        errs.append("行尾残留数字")

    all_ids.extend(learn)
    return errs


total = 0
for d in DAYS:
    errs = check(d)
    total += len(errs)
    print(f"Day{d}: {'OK' if not errs else '问题 ' + str(len(errs))}")
    for e in errs:
        print("   ✗", e)

if sorted(all_ids) == list(range(1001, 2001)):
    print("全表编号 1001–2000 完整且无重复 ✔")
else:
    miss = sorted(set(range(1001, 2001)) - set(all_ids))
    dup = sorted({i for i in all_ids if all_ids.count(i) > 1})
    print(f"全表问题：缺 {len(miss)} 条 {miss[:8]}｜重复 {len(dup)} 条 {dup[:8]}")
    total += 1
print("总问题：", total)
