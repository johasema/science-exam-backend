import json
import os

import streamlit as st

from pdf_parse import extract_pdf

APP_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(APP_DIR, "quiz_database.json")


def load_quiz_list():
    if not os.path.isfile(JSON_PATH):
        return []
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_quiz_list(items):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def merge_by_id(existing, new_items):
    by_id = {str(x["id"]): x for x in existing}
    for it in new_items:
        qid = str(it["id"])
        prev = by_id.get(qid) or {}
        new_images = it.get("image_urls") or []
        by_id[qid] = {
            "id": qid,
            "unit": it["unit"],
            "content": it.get("content") or "",
            "abc": it.get("abc") or "",
            # 추출이 실패하면 빈 리스트가 들어갈 수 있어, 그땐 기존 이미지를 유지합니다.
            "image_urls": new_images if new_images else (prev.get("image_urls") or []),
            "options": it.get("options") or [],
        }
    return [by_id[k] for k in sorted(by_id.keys())]


st.set_page_config(page_title="통합과학 문제 은행", layout="wide")
st.title("🧪 통합과학 문제 은행")

st.subheader("PDF 업로드")
st.caption(
    "형식: `#` + 6자리 ID → 다음 줄 Unit(단원명) → 본문(content) → "
    "줄바꿈 후 `보기` → ㄱㄴㄷ(abc) → ①~⑤ 선택지(options). "
    "추출 결과는 `quiz_database.json`에 저장됩니다(같은 ID는 덮어씀)."
)

uploaded = st.file_uploader(
    "PDF 파일 선택",
    type=["pdf"],
    label_visibility="visible",
)

if st.button("문제 추출 후 JSON 저장", type="primary", disabled=not uploaded):
    tmp = os.path.join(APP_DIR, "uploaded_temp.pdf")
    with open(tmp, "wb") as f:
        f.write(uploaded.getvalue())
    try:
        items = extract_pdf(tmp)
        existing = load_quiz_list()
        merged = merge_by_id(existing, items)
        save_quiz_list(merged)
        st.success(
            f"`{os.path.basename(JSON_PATH)}` 저장 완료: "
            f"이번 PDF에서 `{len(items)}`문항 추출, 전체 `{len(merged)}`문항."
        )
        if items:
            with st.expander("이번 추출 요약"):
                for it in items:
                    u = it["unit"] or "(단원 없음)"
                    preview = u[:50] + ("…" if len(u) > 50 else "")
                    st.write(f"- **{it['id']}** | {preview}")
    except Exception as e:
        st.error(f"처리 실패: {e}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

st.divider()
st.subheader("문제 조회")

db = load_quiz_list()
if not db:
    st.info("먼저 위에서 PDF를 업로드해 `quiz_database.json`을 만드세요.")
else:
    search_id = st.text_input("조회할 문제 ID (6자리)", "")

    if search_id:
        quiz = next((x for x in db if str(x["id"]) == search_id.strip()), None)

        if not quiz:
            st.warning("해당 ID의 문제를 찾을 수 없습니다.")
        else:
            st.markdown(f"### 📍 [ID: {quiz['id']}] {quiz.get('unit', '')}")

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("### **문제 본문 (content)**")
                st.info(quiz.get("content") or "(본문 없음)")

                for img_path in quiz.get("image_urls") or []:
                    p = img_path if os.path.isabs(img_path) else os.path.join(APP_DIR, img_path)
                    if os.path.isfile(p):
                        st.image(
                            p,
                            caption=f"문제 이미지: {quiz['id']}",
                            use_container_width=True,
                        )

                abc_text = (quiz.get("abc") or "").strip()
                if not abc_text and quiz.get("content") and "보기" in quiz["content"]:
                    full = quiz["content"]
                    parts = full.rsplit("보기", 1)
                    if len(parts) == 2:
                        abc_text = "보기" + parts[1].strip()

                if abc_text:
                    formatted = abc_text.replace("7.", "ㄱ.").replace(
                        "ㄴ.", "\n\nㄴ."
                    ).replace("ㄷ.", "\n\nㄷ.")
                    st.markdown("### **보기 (abc)**")
                    st.warning(formatted)

            with col2:
                st.markdown("### **선택지 (options)**")
                for i, opt in enumerate(quiz.get("options") or [], 1):
                    if (opt or "").strip():
                        st.write(f"**{i}번.** {opt}")

            st.success("조회가 완료되었습니다.")
