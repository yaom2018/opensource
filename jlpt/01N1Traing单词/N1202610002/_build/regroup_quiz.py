# -*- coding: utf-8 -*-
"""把日课里的盲测从「100 题 → 统一答案」改成「20 题一组 → 组后立刻折叠答案」。

用法：python _build/regroup_quiz.py "10天背诵/Day11.md" 1001 1100 20
"""
import json
import re
import sys

md_path, lo, hi, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
SIZE = size

data = {e["id"]: e for e in json.load(open("_build/vocab_1001_2000.json", encoding="utf-8"))}
text = open(md_path, encoding="utf-8").read()

i2 = text.index("## 二、2 选 1 盲测")
i3 = text.index("## 四、易混对速记")
head, mid, tail = text[:i2], text[i2:i3], text[i3:]

# ---- 头部：标题与顺序说明 ----
head = head.replace(
    "## 二、2 选 1 盲测（学完再做，20–30 分钟）",
    f"## 二、2 选 1 盲测（{SIZE} 题一组，做完一组立刻对答案）",
)
head = head.replace(
    "> ② 再回**第二节做 2 选 1**：100 题，先别翻第三节答案；选项**故意不标读音**，别靠提示猜",
    f"> ② 再回**第二节做 2 选 1**：**{SIZE} 题一组**，一组做完立刻展开该组的折叠答案；选项**故意不标读音**，别靠提示猜",
)
head = head.replace(
    "> ③ 对答案（第三节折叠）→ 立刻把**第四节「易混对速记」**抄一遍（这一步决定这天记不记得住）",
    "> ③ 每组对完答案 → 立刻把**第三节「易混对速记」**抄一遍（这一步决定这天记不记得住）",
)
head = head.replace(
    "**今天相对 Day08 模板改了什么（5 处）**",
    "**今天相对 Day08 模板改了什么（6 处）**",
)
head = head.replace(
    "| 分组 | 100 词一口气过 | 每 25 词一组（＝教材 1 页），组后 3 分钟快过 | 切小块回头率高；100 词连着背，后面全糊 |",
    "| 学习分组 | 100 词一口气过 | 每 25 词一组（＝教材 1 页），组后 3 分钟快过 | 切小块回头率高；100 词连着背，后面全糊 |\n"
    f"| 盲测答案 | 100 题做完再翻统一答案 | **{SIZE} 题一组，组后立刻折叠给答案** | 一次对 100 个答案太费劲，也对不出「哪一组最弱」 |",
)

# 把「答题卡」整块从原来的第二节里摘出来，稍后放到分组说明后面
m_card = re.search(r"\*\*答题卡.*?```text\n.*?\n```", mid, re.S)
card = m_card.group(0).rstrip("\n")

# ---- 二、盲测：每组 SIZE 题 + 该组折叠答案 ----
lines = []
lines.append(f"## 二、2 选 1 盲测（{SIZE} 题一组，做完一组立刻对答案）")
lines.append("")
lines.append(f"做法：读句子 → 选 A 或 B → 这一组 {SIZE} 题做完，**展开下面该组的折叠答案**立刻批。选完能说出「另一个为什么不行」最好。")
lines.append("")
lines.append("> 选项顺序固定：**A 在左、B 在右**（和教材排版一致），抄答案时直接写 A / B 就行。")
lines.append(">")
lines.append(f"> 分 5 组、每组 {SIZE} 题：错题当场圈出来，直接填到第四节「错题回炉」；**别攒到最后一起对**。")
lines.append("")
lines.append(card)
lines.append("")

total = hi - lo
for g in range((total + SIZE - 1) // SIZE):
    ids = list(range(lo + g * SIZE, min(lo + (g + 1) * SIZE, hi)))
    lines.append(f"### 第 {g + 1} 组（{ids[0]}–{ids[-1]}）")
    lines.append("")
    for wid in ids:
        e = data[wid]
        lines.append(f"**{wid}**　{e['quiz']}")
        lines.append("")
        lines.append(f"　　A {e['optA']}　／　B {e['optB']}　→　我选：____")
        lines.append("")
    lines.append(f"<details><summary>第 {g + 1} 组答案（{ids[0]}–{ids[-1]}）</summary>")
    lines.append("")
    for wid in ids:
        e = data[wid]
        right = e["optA"] if e["ans"] == "A" else e["optB"]
        wrong = e["optB"] if e["ans"] == "A" else e["optA"]
        lines.append(f"{wid}　{e['word']}｜{e['reading']}｜{e['cn']}　→ **{e['ans']}**（正确 {right}／干扰 {wrong}）")
        lines.append("")
    lines.append("</details>")
    lines.append("")

new = "\n".join(lines) + "---\n\n"

# ---- 尾部：小节重新编号（三 易混对 / 四 错题回炉 / 五 排程） ----
tail = tail.replace("## 四、易混对速记", "## 三、易混对速记")
tail = tail.replace("## 五、错题回炉", "## 四、错题回炉")
tail = tail.replace("## 六、+1 / +3 / +7 复习排程", "## 五、+1 / +3 / +7 复习排程")

out = head + new + tail
# 正文里对小节的交叉引用：第四节→第三节（易混对），第五节→第四节（错题回炉 / 台账），第六节→第五节
out = out.replace("第四节「易混对速记」", "第三节「易混对速记」")
out = out.replace("第五节", "第四节")
out = out.replace("第六节", "第五节")

open(md_path, "w", encoding="utf-8").write(out)
print("rewrote", md_path, len(out.splitlines()), "lines")
