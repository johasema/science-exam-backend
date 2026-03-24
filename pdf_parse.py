"""PDF에서 #ID, Unit, content, 보기(abc), ①~⑤ options 추출."""
import os
import re
from pathlib import Path

import fitz  # PyMuPDF

# 원문자 ①–⑤
_CIRC = "\u2460\u2461\u2462\u2463\u2464"


def _parse_options_block(s: str) -> list[str]:
    """① … ② … 형태를 5개 문자열로 분리."""
    s = s.strip()
    if not s:
        return ["", "", "", "", ""]
    positions = []
    for ch in _CIRC:
        positions.append(s.find(ch))
    if all(p == -1 for p in positions):
        # 대체: 1. 2. 3. 4. 5. (줄 시작)
        alt = []
        for i in range(1, 6):
            m = re.search(rf"(?m)^{i}\.\s*", s)
            alt.append(m.start() if m else -1)
        if sum(1 for x in alt if x >= 0) >= 3:
            out = []
            for i in range(5):
                start = alt[i]
                if start == -1:
                    out.append("")
                    continue
                end = len(s)
                for j in range(i + 1, 5):
                    if alt[j] != -1:
                        end = alt[j]
                        break
                line = s[start:end].strip()
                line = re.sub(rf"^{i}\.\s*", "", line)
                out.append(line)
            while len(out) < 5:
                out.append("")
            return out[:5]

    out = []
    for i in range(5):
        start = positions[i]
        if start == -1:
            out.append("")
            continue
        end = len(s)
        for j in range(i + 1, 5):
            if positions[j] != -1:
                end = positions[j]
                break
        chunk = s[start + 1 : end].strip()
        out.append(chunk)
    return out


def _split_bogi_and_rest(rest: str) -> tuple[str, str]:
    """본문 뒤에서 content(보기 전)와 '보기' 이후 전체."""
    rest = rest.strip()
    if not rest:
        return "", ""

    # 문장 속 [보기]가 아닌, 박스 제목으로 쓰인 '보기' (줄 전체 또는 \n보기\n)
    candidates = [
        r"\n\s*보기\s*\n",
        r"\n\s*보기\s*\r\n",
    ]
    for pat in candidates:
        m = re.search(pat, rest)
        if m:
            return rest[: m.start()].strip(), rest[m.end() :].strip()

    m = re.search(r"(?m)^\s*보기\s*$", rest)
    if m:
        return rest[: m.start()].strip(), rest[m.end() :].strip()

    # 마지막 수단: 첫 '보기' 직후 줄바꿈 (문맥상 박스)
    m = re.search(r"(?<!\[)보기(?!\])", rest)
    if m:
        tail = rest[m.end() :].lstrip()
        if tail.startswith("\n") or tail.startswith("\r"):
            return rest[: m.start()].strip(), tail.lstrip("\n\r").strip()

    return rest, ""


def _split_abc_and_options(after_bogi: str) -> tuple[str, str]:
    """ㄱㄴㄷ 보기(abc)와 ① 이후 options."""
    after_bogi = after_bogi.strip()
    if not after_bogi:
        return "", ""

    first_circ = -1
    for ch in _CIRC:
        pos = after_bogi.find(ch)
        if pos != -1 and (first_circ == -1 or pos < first_circ):
            first_circ = pos

    if first_circ == -1:
        m = re.search(r"(?m)^\s*1\.\s+", after_bogi)
        if m:
            first_circ = m.start()
    if first_circ == -1:
        return after_bogi.strip(), ""

    abc = after_bogi[:first_circ].strip()
    options_text = after_bogi[first_circ:].strip()
    return abc, options_text


def parse_problem_block(block: str) -> dict | None:
    """
    한 문제 텍스트 블록 (#123456 으로 시작) 파싱.
    """
    raw = block.strip()
    if not raw:
        return None

    lines = raw.splitlines()
    m0 = re.match(r"#\s*(\d{6})\s*", lines[0].strip() if lines else "")
    if not m0:
        return None

    qid = m0.group(1)
    unit = ""
    if len(lines) > 1:
        unit = lines[1].strip()
        unit = re.sub(r"^Unit\s*:?\s*", "", unit, flags=re.I).strip()

    rest = "\n".join(lines[2:]).strip()

    content_pre, after_bogi = _split_bogi_and_rest(rest)
    abc, options_raw = _split_abc_and_options(after_bogi)
    options = _parse_options_block(options_raw)

    return {
        "id": qid,
        "unit": unit,
        "content": content_pre,
        "abc": abc,
        "options": options,
    }


def _split_into_problem_blocks(full_text: str) -> list[str]:
    parts = re.split(r"(?=#\s*\d{6})", full_text)
    out = []
    for p in parts:
        p = p.strip()
        if re.match(r"#\s*\d{6}", p):
            out.append(p)
    return out


def extract_pdf(pdf_path: str | Path, images_dir: str | Path | None = None) -> list[dict]:
    """
    PDF 전체 파싱. 페이지별 텍스트를 이어붙인 뒤 #ID 기준으로 분할.
    이미지는 페이지에 나타난 순서로 해당 페이지의 문제 ID에 연결
    (한 페이지에 한 문제일 때 가장 안정적).
    """
    pdf_path = Path(pdf_path)
    images_dir = Path(images_dir) if images_dir else Path(__file__).resolve().parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    page_texts: list[str] = []
    page_ids: list[list[str]] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text()
        page_texts.append(text)
        ids = re.findall(r"#\s*(\d{6})", text)
        page_ids.append(ids)

    full_text = "\n\n".join(page_texts)
    blocks = _split_into_problem_blocks(full_text)

    parsed: dict[str, dict] = {}
    order: list[str] = []

    for block in blocks:
        q = parse_problem_block(block)
        if not q:
            continue
        qid = q["id"]
        if qid not in parsed:
            order.append(qid)
        parsed[qid] = q

    # 이미지: 문제 구간(#ID ~ 다음 #ID) 안에 있는 "그림 영역"만 모아서 한 덩어리로 저장
    # (이전 구현은 page.get_images()가 페이지의 모든 이미지 조각을 반환해서 분할/오부착이 많았음)
    id_to_images: dict[str, list[str]] = {qid: [] for qid in order}

    # 1) 각 페이지에서 '#123456'이 나타나는 y좌표(첫 등장)를 찾습니다.
    def _extract_id_positions() -> dict[str, tuple[int, float]]:
        positions: dict[str, tuple[int, float]] = {}
        id_pat = re.compile(r"#\s*(\d{6})")

        for page_index in range(len(doc)):
            page = doc[page_index]
            try:
                d = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)
            except TypeError:
                # PyMuPDF 버전별로 flags 인자가 없을 수 있어 호환
                d = page.get_text("dict")

            for block in d.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", []) or []
                    line_text = "".join((sp.get("text") or "") for sp in spans)
                    if "#" not in line_text:
                        continue

                    # y는 span 여러 조각으로 쪼개져도, 라인에서 가장 위쪽 값을 사용합니다.
                    ys = []
                    for sp in spans:
                        bbox = sp.get("bbox")
                        if bbox and len(bbox) == 4:
                            ys.append(float(bbox[1]))
                    if ys:
                        y0 = min(ys)
                    else:
                        lb = line.get("bbox")
                        y0 = float(lb[1]) if lb and len(lb) == 4 else 0.0

                    # '#'가 라인 시작에 있을 때만 "문제 시작"으로 더 강하게 간주
                    m_start = re.match(r"^\s*#\s*(\d{6})", line_text)
                    if m_start:
                        qid = m_start.group(1)
                        old = positions.get(qid)
                        # 같은 ID가 여러 번 잡히면 더 위(y가 작은) 등장 위치를 사용
                        if old is None or (old[0] == page_index and y0 < old[1]):
                            positions[qid] = (page_index, y0)
                        continue

                    # 라인 시작이 아니면, 그래도 '다른 위치에 #ID가 있긴 한' 경우를 위해 최대 1개만 보정
                    m_all = list(id_pat.finditer(line_text))
                    if not m_all:
                        continue
                    qid = m_all[0].group(1)
                    old = positions.get(qid)
                    if old is None or (old[0] == page_index and y0 < old[1]):
                        positions[qid] = (page_index, y0)

            # order에 없는 ID는 무시해도 되지만, 여기서는 간단히 전체를 모읍니다.
        return positions

    id_first_pos = _extract_id_positions()

    # 2) 페이지 내에서 ID들의 y를 정렬한 뒤,
    #    각 문제의 경계를 "다음 ID 시작 y의 중간(midpoint)"으로 잡습니다.
    intervals_by_page: dict[int, list[tuple[str, float, float]]] = {}
    start_eps = 0.3
    end_eps = 0.3
    for page_index in range(len(doc)):
        page = doc[page_index]
        ids_on_page = [(qid, id_first_pos[qid][1]) for qid in order if qid in id_first_pos and id_first_pos[qid][0] == page_index]
        if not ids_on_page:
            continue
        ids_on_page.sort(key=lambda t: t[1])
        for i, (qid, y0) in enumerate(ids_on_page):
            y_low = y0 + start_eps
            if i + 1 < len(ids_on_page):
                y_next = ids_on_page[i + 1][1]
                boundary = (y0 + y_next) / 2.0
                y_high = boundary - end_eps
            else:
                y_high = float(page.rect.height)
            if y_high > y_low:
                intervals_by_page.setdefault(page_index, []).append((qid, y_low, y_high))

    # 3) 이미지 바운딩박스를 모아서 y구간에 맞게 클립으로 렌더링합니다.
    def _extract_image_bboxes(page) -> list[fitz.Rect]:
        try:
            d = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)
        except TypeError:
            d = page.get_text("dict")

        bboxes: list[fitz.Rect] = []
        for block in d.get("blocks", []):
            t = block.get("type")
            # type==1 이 이미지인 경우가 많지만, 버전에 따라 달라질 수 있어 bbox/xref가 있는 경우만 채택
            if t == 0:
                continue
            if t not in (1, 2) and not (block.get("xref") is not None or block.get("image") is not None):
                continue
            bbox = block.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            bboxes.append(fitz.Rect(bbox))
        return bboxes

    any_bbox_found = False
    # included는 "이미지 bbox의 중심 y"가 문제 구간에 들어갈 때만 포함합니다.

    for page_index in range(len(doc)):
        page = doc[page_index]
        img_bboxes = _extract_image_bboxes(page)
        if img_bboxes:
            any_bbox_found = True

        if not img_bboxes:
            continue

        # 현재 페이지에서 활성 구간이 되는 qid들만 처리
        for qid, y_low, y_high in intervals_by_page.get(page_index, []):

            # y구간을 벗어나면 skip
            if y_high <= y_low:
                continue

            included: list[fitz.Rect] = []
            for r in img_bboxes:
                cy = (r.y0 + r.y1) / 2.0
                if y_low <= cy < y_high:
                    included.append(r)

            if not included:
                continue

            # 포함된 이미지 bbox들을 union 해서 "한 덩어리"로 저장
            ux0 = min(r.x0 for r in included)
            uy0 = min(r.y0 for r in included)
            ux1 = max(r.x1 for r in included)
            uy1 = max(r.y1 for r in included)
            union_rect = fitz.Rect(ux0, uy0, ux1, uy1)

            # 너무 작은 경우(오인식) 스킵
            if union_rect.get_area() < 5000:
                continue

            # 렌더링 품질(배율)을 올려 글씨가 필요하면 선명하게,
            # 그림만 필요한 경우에도 끊김을 줄입니다.
            pix = page.get_pixmap(clip=union_rect, matrix=fitz.Matrix(2, 2), alpha=False)
            fname = f"{qid}_{page_index}_img.png"
            fpath = images_dir / fname
            pix.save(str(fpath))
            id_to_images[qid].append(str(fpath))

    # 4) dict("dict")에서 이미지 bbox를 못 찾는 PDF면(버전/폰트/레이아웃 문제),
    # 기존 방식으로 최소한의 결과를 내기 위해 fallback을 수행합니다.
    if not any_bbox_found or not intervals_by_page:
        for page_index in range(len(doc)):
            page = doc[page_index]
            ids_on_page = list(dict.fromkeys(page_ids[page_index]))
            if not ids_on_page:
                continue
            target_id = ids_on_page[0]

            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base = doc.extract_image(xref)
                except Exception:
                    continue
                ext = base.get("ext", "png") or "png"
                fname = f"{target_id}_{page_index}_{img_index}.{ext}"
                fpath = images_dir / fname
                with open(fpath, "wb") as f:
                    f.write(base["image"])
                id_to_images.setdefault(target_id, []).append(str(fpath))

    out_list: list[dict] = []
    for qid in order:
        item = parsed[qid]
        item["image_urls"] = id_to_images.get(qid, [])
        out_list.append(item)

    doc.close()
    return out_list
