# -*- coding: utf-8 -*-
"""把 N1語彙1001-2000簡体字.pdf 解析成结构化 JSON。

PDF 是固定列的表格：番号 | 単語 | 読み | 中国語 | 日本語意味 | 例文 | 訳文 | 穴埋め問題 | 選択肢A | 選択肢B
按字的 x 坐标分列，按 y 坐标聚行，再按「番号」行切出每个词条。
"""
import json
import re
import unicodedata

import fitz

PDF = r"N1語彙1001-2000簡体字.pdf.pdf"

# x0 分列边界（实测所有页锚点固定在 66/124/182/232/318/434/556/689/739）
BANDS = [
    ("num", -1, 63),
    ("word", 63, 120),
    ("read", 120, 180),
    ("cn", 180, 230),
    ("jp", 230, 316),
    ("ex", 316, 430),
    ("tr", 430, 550),
    ("quiz", 550, 680),
    ("optA", 680, 730),
    ("optB", 730, 1e9),
]

KANA = re.compile(r"[ぁ-んァ-ヶー]")
CJK = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# PDF 里混进来的「部首补充区」字符（U+2E80–U+2EFF 没有 NFKC 映射，只能手写对照）
RADICAL_MAP = {
    "⺠": "民", "⺟": "母", "⺩": "王", "⺫": "目", "⺬": "示", "⺭": "示",
    "⺮": "竹", "⺶": "羊", "⺷": "羊", "⺸": "羊", "⺹": "老", "⺺": "肀",
    "⺼": "月", "⺾": "艹", "⺿": "艹", "⻀": "艹", "⻁": "虎", "⻂": "衤",
    "⻃": "西", "⻄": "西", "⻅": "见", "⻆": "角", "⻈": "讠", "⻊": "足",
    "⻋": "车", "⻌": "辶", "⻍": "辶", "⻎": "辶", "⻏": "阝", "⻐": "钅",
    "⻑": "長", "⻒": "镸", "⻓": "长", "⻔": "门", "⻖": "阝", "⻗": "雨",
    "⻘": "青", "⻚": "页", "⻛": "风", "⻜": "飞", "⻝": "食", "⻞": "飠",
    "⻟": "飠", "⻠": "饣", "⻡": "馬", "⻢": "马", "⻣": "骨", "⻤": "鬼",
    "⻥": "鱼", "⻦": "鸟", "⻧": "卤", "⻨": "麦", "⻩": "黄", "⻪": "黾",
    "⻫": "斉", "⻬": "齐", "⻭": "歯", "⻮": "齿", "⻯": "竜", "⻰": "龙",
    "⻱": "龜", "⻲": "亀", "⻳": "龟",
}


def fix_compat(s: str) -> str:
    """把 PDF 里混进来的康熙部首 / 部首补充 / 兼容汉字（⾼⽇⼼⻓⻅…）还原成标准汉字。"""
    out = []
    for ch in s:
        if ch in RADICAL_MAP:
            out.append(RADICAL_MAP[ch])
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            out.append(ch)
            continue
        if name.startswith(("KANGXI RADICAL", "CJK COMPATIBILITY IDEOGRAPH")):
            out.append(unicodedata.normalize("NFKC", ch))
        else:
            out.append(ch)
    return "".join(out)


def band_of(x0: float) -> str:
    for name, lo, hi in BANDS:
        if lo <= x0 < hi:
            return name
    return "jp"


def page_lines(page):
    """把一页的单词按 y 聚成视觉行（容差 2.5pt），返回 [(y, {band: text})]。"""
    words = sorted(page.get_text("words"), key=lambda w: (w[1], w[0]))
    groups = []
    for w in words:
        if groups and abs(w[1] - groups[-1][0][1]) <= 2.5:
            groups[-1].append(w)
        else:
            groups.append([w])
    lines = []
    for g in groups:
        per = {}
        for x0, y0, x1, y1, text, *_ in sorted(g, key=lambda w: w[0]):
            per.setdefault(band_of(x0), []).append(text)
        lines.append((min(w[1] for w in g), {k: "".join(v) for k, v in per.items()}))
    return lines


def join_text(parts):
    return "".join(parts).replace("　", "").strip()


def split_ja_zh(text: str):
    """把粘在一起的「日文部分 + 中文译文」切开：返回 (日文, 中文)。"""
    # 从尾部往前找最长的「不含假名」的中文尾巴（>= 4 字，且前面是句读）
    n = len(text)
    i = n
    while i > 0 and not KANA.match(text[i - 1]):
        i -= 1
    tail = text[i:]
    if i > 0 and len(tail) >= 4 and CJK.search(tail):
        head = text[:i]
        # 尾巴开头的标点还给日文
        while tail and tail[0] in "。、，, ":
            head += tail[0]
            tail = tail[1:]
        if tail:
            return head, tail
    return text, ""


def split_example_from_jp(jp_text: str, word: str, quiz: str):
    """日本語意味里混进了例句（甚至译文）时切开。

    例: 「①最後の最後まで。徹底的に彼はとことんまでやり抜く性格で、最後まで」
    """
    # 先按「quiz 的前缀出现在 jp 里」定位例句起点
    for k in range(8, 3, -1):
        prefix = quiz[:k]
        if prefix and prefix in jp_text and not jp_text.startswith(prefix):
            idx = jp_text.index(prefix)
            return jp_text[:idx], jp_text[idx:]
    if "。" not in jp_text:
        return jp_text, ""
    idx = jp_text.find("。")
    head, rest = jp_text[: idx + 1], jp_text[idx + 1 :]
    if not rest:
        return jp_text, ""
    stem = re.sub(r"（[^）]*）", "", word)
    stem = re.sub(r"(する|な|と)$", "", stem)
    stem = stem[:2] if len(stem) >= 2 else stem
    if stem and stem in rest and len(rest) >= 8:
        return head, rest
    return jp_text, ""


def normalize_blank(text: str) -> str:
    return re.sub(r"（[\s_＿]*）", "（_______）", text)


# 个别词条在 PDF 里整格塌成一行、无法用规则切开，人工核对后写死
OVERRIDES = {
    1042: {
        "jp": "①力や気力が残っている状態。",
        "example": "今日は疲れて、夕食を作る余力もなかった。",
        "trans": "今天累得连做晚饭的力气都没有了。",
    },
    # 教材这一行排版坏了：题目没留空格、只给了一个选项
    1246: {
        "quiz": "展示会のために、博物館から資料を（_______）。",
        "optA": "借金した",
        "optB": "借用した",
    },
    1400: {
        "quiz": "（_______）は国をまとめて政治を行う役割がある。",
        "optA": "内閣",
        "optB": "内訳",
        "note": "干扰项为补充（教材此题只给了一个选项）",
    },
    1547: {
        "quiz": "彼は自分のミスをまるで（_______）のように話している。",
        "optA": "人事",
        "optB": "他人事",
        "note": "干扰项为补充（教材此题只给了一个选项）",
    },
    1711: {
        "quiz": "たまには（_______）を吐いたっていいじゃないか？",
        "optA": "弱音",
        "optB": "弱点",
    },
    1934: {"optA": "立て替え払いした", "optB": "立て直した"},
    1956: {
        "jp": "①厚くてしっかりしている様子。",
        "example": "冬は厚手のコートをよく着ている。",
    },
    1963: {
        "jp": "①物の重さの中心となる部分。",
        "example": "重心が高いと転びやすい。",
    },
    1485: {
        "quiz": "協議の末、A社とB社は（_______）。",
        "trans": "经过协商，A公司与B公司达成了和解。",
    },
    1735: {
        "quiz": "A国政府はB国政府に対して、（_______）な態度をとり続けている。",
        "trans": "A国政府一直对B国政府采取强硬态度。",
    },
}


def parse():
    doc = fitz.open(PDF)
    entries = []
    for pno, page in enumerate(doc, start=1):
        lines = page_lines(page)
        nums = []
        for y, per in lines:
            num = per.get("num", "").strip()
            if re.fullmatch(r"\d+", num):
                nums.append((y, int(num)))
        nums.sort()
        word_lines = [(y, per.get("word", "")) for y, per in lines if per.get("word")]
        for i, (y0, num) in enumerate(nums):
            y_end = nums[i + 1][0] if i + 1 < len(nums) else 1e9
            y_start = y0 - 3.0
            word = ""
            for wy, wtxt in word_lines:
                if abs(wy - y0) <= 4.0:
                    word = wtxt
                    break
            cell = {k: [] for k in ("read", "cn", "jp", "ex", "tr", "quiz", "optA", "optB")}
            for y, per in lines:
                if y_start <= y < y_end - 3.0:
                    for k in cell:
                        if k in per:
                            cell[k].append(per[k])

            quiz = normalize_blank(join_text(cell["quiz"]))
            jp_raw = join_text(cell["jp"])
            jp, ex_tail = split_example_from_jp(jp_raw, word, quiz)
            ex = ex_tail + join_text(cell["ex"])
            tr = join_text(cell["tr"])
            optA = join_text(cell["optA"])
            optB = join_text(cell["optB"])

            # 选项 A 有时被并进题目文字里
            if not optA and "。" in quiz:
                head, rest = quiz.rsplit("。", 1)
                if rest and len(rest) <= 12:
                    quiz, optA = head + "。", rest

            # 长外来语词条：单词 / 读音 / 中文黏成一格
            m = re.match(r"^(.*?（する）)(.*?（する）)(.*)$", word)
            if m and not join_text(cell["read"]) and not join_text(cell["cn"]):
                word, reading, cn = m.group(1), m.group(2), m.group(3)
            else:
                reading, cn = join_text(cell["read"]), join_text(cell["cn"])
            # 先把兼容/部首字符还原，后面的切分规则才认得出汉字
            word, reading, cn = fix_compat(word), fix_compat(reading), fix_compat(cn)

            # 中文被并进读音格：末尾的汉字串切出来
            if not cn and KANA.search(reading):
                m2 = re.search(r"[\u4e00-\u9fff][\u4e00-\u9fff,，、\s]*$", reading)
                if m2 and m2.start() > 0:
                    cn = reading[m2.start() :].strip()
                    reading = reading[: m2.start()]

            # 译文被并进例句里
            if not tr:
                ex, tail = split_ja_zh(ex)
                tr = tail
            # 译文格里混进了题目文字：把含空格的片段连同后面的都切掉
            if "（_______）" in tr:
                keep = []
                for seg in re.split(r"(?<=。)", tr):
                    if "（_______）" in seg:
                        break
                    keep.append(seg)
                tr = "".join(keep).strip()
            # 题目格是空的：题目文字落在译文格里
            if "（_______）" not in quiz:
                for seg in re.split(r"(?<=。)|\n", join_text(cell["tr"])):
                    if "（_______）" in seg:
                        quiz = seg.strip() + quiz
                        break
            # 例句 + 译文都塌进「日文意味」格里
            if not ex and not tr:
                jp, tail = split_ja_zh(jp)
                ex, tr2 = split_ja_zh(tail)
                tr = tr2 or tr

            e = {
                "id": 1000 + num,
                "pdf_no": num,
                "page": pno,
                "word": fix_compat(word),
                "reading": fix_compat(reading),
                "cn": fix_compat(cn),
                "jp": fix_compat(jp),
                "example": fix_compat(ex),
                "trans": fix_compat(tr),
                "quiz": quiz,
                "optA": fix_compat(optA),
                "optB": fix_compat(optB),
            }
            if e["id"] in OVERRIDES:
                e.update({k: fix_compat(v) for k, v in OVERRIDES[e["id"]].items()})
            entries.append(e)
    return entries


def pick_answer(e):
    """正确选项 = 原样出现在例句里的那个。"""
    ex = e["example"]
    a, b = e["optA"], e["optB"]
    a_in, b_in = bool(a) and a in ex, bool(b) and b in ex
    if a_in and not b_in:
        return "A"
    if b_in and not a_in:
        return "B"
    if a_in and b_in:  # 两个都出现，取更长的那个（通常是完整词形）
        return "A" if len(a) > len(b) else "B"
    # 都不在例句里（教材例句用了简写）：取和词头最像的那个
    def prefix(x, y):
        k = 0
        while k < min(len(x), len(y)) and x[k] == y[k]:
            k += 1
        return k

    pa, pb = prefix(a, e["word"]), prefix(b, e["word"])
    if pa != pb:
        return "A" if pa > pb else "B"
    stem = re.sub(r"（[^）]*）", "", e["word"])
    stem = re.sub(r"する$", "", stem)
    stem = stem[:-1] if len(stem) > 1 else stem
    if stem and a.startswith(stem):
        return "A"
    if stem and b.startswith(stem):
        return "B"
    return ""


def incomplete(e):
    bad = []
    if not e["word"]:
        bad.append("word")
    if not e["reading"]:
        bad.append("reading")
    if not e["cn"]:
        bad.append("cn")
    if not e["jp"] or not e["jp"].startswith("①"):
        bad.append("jp")
    if not e["example"] or not KANA.search(e["example"]):
        bad.append("example")
    if not e["trans"] or KANA.search(e["trans"]):
        bad.append("trans")
    if "（_______）" not in e["quiz"]:
        bad.append("quiz")
    if not e["optA"]:
        bad.append("optA")
    if not e["optB"]:
        bad.append("optB")
    if not e["ans"]:
        bad.append("ans")
    return bad


if __name__ == "__main__":
    data = parse()
    for e in data:
        e["ans"] = pick_answer(e)
        e["issues"] = incomplete(e)
    with open("_build/vocab_1001_2000.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    bad = [e for e in data if e["issues"]]
    print("entries:", len(data), "incomplete:", len(bad))
    for e in bad:
        print(" BAD", e["id"], e["word"], e["issues"])
