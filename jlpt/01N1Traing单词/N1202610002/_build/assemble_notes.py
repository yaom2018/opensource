# -*- coding: utf-8 -*-
"""把 _build/notes/DayNN.md 的四块内容注入到骨架 10天背诵/DayNN.md 的占位符。

notes 文件用 @@GROUPS@@ / @@COLLOC@@ / @@NUANCE@@ / @@CONFUSE@@ 分段。
用法：python _build/assemble_notes.py 12 [13 ...]
"""
import os
import re
import sys

KEYS = ("GROUPS", "COLLOC", "NUANCE", "CONFUSE")


def load_blocks(path):
    text = open(path, encoding="utf-8").read()
    parts = re.split(r"^@@(\w+)@@\s*$", text, flags=re.M)
    blocks = {}
    for i in range(1, len(parts), 2):
        blocks[parts[i]] = parts[i + 1].strip("\n")
    missing = [k for k in KEYS if not blocks.get(k, "").strip()]
    return blocks, missing


def main():
    for day in sys.argv[1:]:
        n = int(day)
        note = f"_build/notes/Day{n:02d}.md"
        target = f"10天背诵/Day{n:02d}.md"
        blocks, missing = load_blocks(note)
        if missing:
            print(f"Day{n:02d}: 缺块 {missing} — 跳过")
            continue
        md = open(target, encoding="utf-8").read()
        for key in KEYS:
            token = f"<!--PLACEHOLDER:{key}-->"
            if token not in md:
                print(f"Day{n:02d}: 占位符 {token} 不在文件里 — 跳过")
                break
            md = md.replace(token, blocks[key])
        else:
            open(target, "w", encoding="utf-8").write(md)
            left = sum(md.count(f"<!--PLACEHOLDER:{k}-->") for k in KEYS)
            print(f"Day{n:02d}: 已注入，剩余占位符 {left}，行数 {len(md.splitlines())}")


if __name__ == "__main__":
    main()
