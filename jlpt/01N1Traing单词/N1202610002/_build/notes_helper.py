# -*- coding: utf-8 -*-
"""Day 文件编写辅助：
  python _build/notes_helper.py words 1101 1200   # 紧凑词表（id|词|读音|中文|A|B|ans）
  python _build/notes_helper.py pairs 1101 1200   # 易混对候选（正确 vs 干扰 + 关系标签）
  python _build/notes_helper.py groups 1101 1200  # 词群候选（同前缀/同后缀/同词性）
"""
import json
import re
import sys

data = {e["id"]: e for e in json.load(open("_build/vocab_1001_2000.json", encoding="utf-8"))}


def entries(lo, hi):
    return [data[i] for i in range(lo, hi) if i in data]


def kana_only(s):
    return bool(re.fullmatch(r"[\u3040-\u309f\u30a0-\u30ffー・（）]+", s))


def kanji(s):
    return [c for c in s if "\u4e00" <= c <= "\u9fff"]


mode, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
es = entries(lo, hi)

if mode == "words":
    for e in es:
        print(f"{e['id']} | {e['word']} | {e['reading']} | {e['cn']} | A {e['optA']} | B {e['optB']} | {e['ans']}")

elif mode == "pairs":
    for e in es:
        right = e["optA"] if e["ans"] == "A" else e["optB"]
        wrong = e["optB"] if e["ans"] == "A" else e["optA"]
        tags = []
        if len(right) == len(wrong) and right[:1] == wrong[:1]:
            tags.append("同首字同长")
        k_r, k_w = kanji(right), kanji(wrong)
        shared = set(k_r) & set(k_w)
        if shared:
            tags.append("共字:" + "".join(sorted(shared)))
        if kana_only(right) and kana_only(wrong):
            if len(right) == len(wrong):
                diff = sum(1 for a, b in zip(right, wrong) if a != b)
                if diff <= 2:
                    tags.append(f"假名近邻({diff})")
        if k_r and not k_w:
            tags.append("漢語vs仮名")
        if any(c in right for c in "（"):
            tags.append("词尾形")
        print(f"{e['id']} | C {right} | D {wrong} | {' / '.join(tags) or '-'} | 题:{e['quiz'][:34]}")

elif mode == "groups":
    def cluster(keyfn, name):
        d = {}
        for e in es:
            k = keyfn(e["word"])
            if k:
                d.setdefault(k, []).append(e)
        out = [(k, v) for k, v in d.items() if len(v) >= 2]
        if out:
            print(f"== {name}")
            for k, v in out:
                print(f"  {k}: " + " / ".join(f"{x['word']}({x['id']})" for x in v))

    cluster(lambda w: w[:2] if len(w) >= 3 and kanji(w[:1]) else None, "同二字前缀")
    cluster(lambda w: w[-2:] if len(w) >= 3 and kanji(w[-1:]) else None, "同二字后缀")
    cluster(lambda w: w.replace("（する）", "").replace("（な）", "") if w.endswith(("（する）", "（な）")) else None, "词尾同形（する/な）")
    cluster(lambda w: "カタカナ" if kana_only(w) and any("\u30a0" <= c <= "\u30ff" for c in w) else None, "片假名")
    cluster(lambda w: "かな体言" if kana_only(w) and all("\u3040" <= c <= "\u309f" or c == "ー" for c in w) else None, "平假名词")
