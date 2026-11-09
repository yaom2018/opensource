# -*- coding: utf-8 -*-
"""解析结果自检：查字段缺失、例句/题干不一致、异常字符。"""
import json
import re
import sys

KANA = re.compile(r"[ぁ-んァ-ヶー]")
data = json.load(open("_build/vocab_1001_2000.json", encoding="utf-8"))
lo = int(sys.argv[1]) if len(sys.argv) > 1 else 1001
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 2000

problems = 0
for e in data:
    if not (lo <= e["id"] < hi):
        continue
    msgs = []
    if e["issues"]:
        msgs.append("missing:" + ",".join(e["issues"]))
    # 题干去掉空格后，各片段应出现在例句里
    for part in e["quiz"].split("（_______）"):
        part = part.strip("、。 ")
        if len(part) >= 4 and part not in e["example"]:
            msgs.append(f"quiz≠example: {part!r}")
            break
    # 正确项应出现在例句里
    right = e["optA"] if e["ans"] == "A" else e["optB"]
    if right and right not in e["example"]:
        msgs.append(f"ans not in example: {right!r}")
    # 异常字符
    for k in ("word", "reading", "cn", "jp", "example", "trans", "quiz", "optA", "optB"):
        for ch in str(e.get(k, "")):
            o = ord(ch)
            if 0x2E80 <= o <= 0x2FFF or 0xF900 <= o <= 0xFAFF:
                msgs.append(f"bad-char {ch!r} in {k}")
    if msgs:
        problems += 1
        print(e["id"], e["word"], "|", " ; ".join(msgs))
print("checked", lo, "-", hi - 1, "problems:", problems)
