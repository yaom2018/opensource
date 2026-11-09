# -*- coding: utf-8 -*-
"""校验 _build/notes/DayNN.md 的四块自定义内容（结构 + 与 JSON 的一致性）。

用法：python _build/check_notes.py 12 13 ... 20
"""
import json
import re
import sys

data = {e["id"]: e for e in json.load(open("_build/vocab_1001_2000.json", encoding="utf-8"))}


def norm(w):
    w = re.sub(r"（.*?）", "", w).strip()
    return w.lstrip("～〜")


def like(a, b):
    """允许活用差异：失効 vs 失効して / 切り上げる vs 切り上げましょう"""
    return a == b or a.startswith(b) or b.startswith(a)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def day_entries(day):
    lo = 1001 + (day - 11) * 100
    return [data[i] for i in range(lo, lo + 100)]


def check(day):
    path = f"_build/notes/Day{day:02d}.md"
    text = open(path, encoding="utf-8").read()
    es = day_entries(day)
    words = {}
    opts = {}
    for e in es:
        words[norm(e["word"])] = e["id"]
        opts[e["id"]] = {norm(e["optA"]), norm(e["optB"])}
    all_opt_words = set()
    for e in es:
        all_opt_words |= opts[e["id"]]

    errs, warns = [], []
    parts = re.split(r"^@@(\w+)@@\s*$", text, flags=re.M)
    blocks = {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}
    order = [p for p in re.findall(r"^@@(\w+)@@", text, flags=re.M)]
    if order != ["GROUPS", "COLLOC", "NUANCE", "CONFUSE"]:
        errs.append(f"分段顺序不对：{order}")
    for k in ("GROUPS", "COLLOC", "NUANCE", "CONFUSE"):
        if not blocks.get(k, "").strip():
            errs.append(f"{k} 为空")
    if "待补" in text or "TODO" in text:
        errs.append("还有『待补/TODO』")
    odd = {c for c in text if 0x2E80 <= ord(c) <= 0x2FFF or 0xF900 <= ord(c) <= 0xFAFF}
    if odd:
        errs.append(f"异常字符：{''.join(sorted(odd))}")

    # ---- 表格列数一致性 ----
    for key in ("GROUPS", "COLLOC", "CONFUSE"):
        rows = [l for l in blocks.get(key, "").splitlines() if l.strip().startswith("|")]
        if len(rows) < 2:
            errs.append(f"{key} 表格行数太少（{len(rows)}）")
            continue
        ncol = len(cells(rows[0]))
        for r in rows:
            if len(cells(r)) != ncol:
                errs.append(f"{key} 列数不一致：{r[:40]}")
                break

    # ---- 搭配表：首列词必须在当天词表里 ----
    colloc = [l for l in blocks.get("COLLOC", "").splitlines() if l.strip().startswith("|")]
    colloc = colloc[2:] if len(colloc) > 2 else []
    n_colloc = 0
    for r in colloc:
        c = cells(r)
        if not c or not c[0] or set(c[0]) <= set("- "):
            continue
        head = c[0].split()[0]
        n_colloc += 1
        if norm(head) not in words:
            warns.append(f"搭配词不在当天词表：{head}（{c[0]}）")

    # ---- 易混对：要记的词在当天词表，别混成必须是该题的另一个选项 ----
    conf = [l for l in blocks.get("CONFUSE", "").splitlines() if l.strip().startswith("|")]
    conf = conf[2:] if len(conf) > 2 else []
    n_conf, n_homophone = 0, 0
    for r in conf:
        c = cells(r)
        if len(c) < 4:
            errs.append(f"易混对行格式异常：{r[:40]}")
            continue
        n_conf += 1
        a = c[1].replace("⚠️", "").split()[0] if c[1].replace("⚠️", "").split() else ""
        b = c[2].replace("⚠️", "").split()[0] if c[2].replace("⚠️", "").split() else ""
        if "⚠️" in c[2] or "同音" in c[3]:
            n_homophone += 1
        if norm(a) not in words:
            # 允许「～ずくめ」这类前缀写法差异
            cand = [w for w in words if like(norm(a), w)]
            if not cand:
                errs.append(f"易混对要记的词不在当天词表：{a}")
                continue
            a_norm = cand[0]
        else:
            a_norm = norm(a)
        wid = words[a_norm]
        pair = opts[wid]
        if not any(like(norm(b), p) for p in pair):
            warns.append(f"别混成不是该题选项（课外同音/近形）：{a} vs {b}")

    # ---- 词群里的编号必须落在当天范围 ----
    lo, hi = es[0]["id"], es[-1]["id"]
    for m in re.finditer(r"(\d{4})", blocks.get("GROUPS", "")):
        wid = int(m.group(1))
        if not (lo <= wid <= hi):
            errs.append(f"词群编号越界：{wid}（当天 {lo}–{hi}）")

    print(f"Day{day:02d}: 搭配 {n_colloc} 行 / 易混对 {n_conf} 行（同音 {n_homophone}）｜问题 {len(errs)}｜提示 {len(warns)}")
    for e in errs:
        print("  ✗", e)
    for w in warns[:12]:
        print("  ! ", w)
    if len(warns) > 12:
        print(f"  !  ...还有 {len(warns) - 12} 条提示")
    return len(errs)


if __name__ == "__main__":
    total = 0
    for d in sys.argv[1:]:
        total += check(int(d))
    print("总问题：", total)
