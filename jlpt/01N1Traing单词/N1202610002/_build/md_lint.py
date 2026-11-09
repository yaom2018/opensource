# -*- coding: utf-8 -*-
"""轻量 Markdown 体检：表格列数是否一致、代码围栏是否闭合、连续空行。"""
import sys

path = sys.argv[1]
lines = open(path, encoding="utf-8").read().splitlines()
errs = []
fence = 0
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("```"):
        fence ^= 1
    if line.startswith("|"):
        block = []
        while i < len(lines) and lines[i].startswith("|"):
            block.append((i + 1, lines[i]))
            i += 1
        widths = {len(r.split("|")) for _, r in block}
        if len(widths) > 1:
            errs.append(f"第 {block[0][0]} 行起的表格列数不一致：{sorted(widths)}")
        continue
    if i >= 2 and line == "" and lines[i - 1] == "" and lines[i - 2] == "":
        errs.append(f"第 {i + 1} 行连续 3 个空行")
    i += 1
if fence:
    errs.append("代码围栏 ``` 没有闭合")
print("问题：", len(errs))
for e in errs:
    print(" -", e)
