import json
import os
import tempfile
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import Base, engine, get_db
from models import Question
from schemas import MemberCheckRequest, MemberCheckResponse
from services import (
    check_member_via_external_api,
    get_or_create_user,
    upsert_questions_from_pdf,
)

app = FastAPI(title="Science Exam Backend", version="0.1.0")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/auth/check-member", response_model=MemberCheckResponse)
def check_member(payload: MemberCheckRequest, db: Annotated[Session, Depends(get_db)]):
    is_member = check_member_via_external_api(payload.name, payload.phone)
    user = get_or_create_user(db, payload.name, payload.phone, is_member)
    msg = "기존 회원입니다." if is_member else "회원 정보가 없습니다."
    return MemberCheckResponse(is_member=is_member, user_id=user.id, message=msg)


@app.post("/admin/import-pdf")
async def import_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        inserted = upsert_questions_from_pdf(db, tmp_path, source_file=file.filename)
        total = db.scalar(select(func.count(Question.id))) or 0
        return {
            "message": "PDF 추출 및 DB 저장 완료",
            "inserted_or_updated": inserted,
            "total_questions": total,
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/questions/{question_id}")
def get_question(question_id: str, db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="문항을 찾을 수 없습니다.")
    return {
        "id": q.id,
        "unit": q.unit,
        "content": q.content,
        "abc": q.abc,
        "options": json.loads(q.options_json or "[]"),
        "image_urls": json.loads(q.image_urls_json or "[]"),
        "answer": q.answer,
    }


@app.get("/questions")
def list_questions(
    units: Annotated[list[str] | None, Query()] = None,
    limit: int = 20,
    random: bool = True,
    db: Session = Depends(get_db),
):
    stmt = select(Question)
    if units:
        stmt = stmt.where(Question.unit.in_(units))
    if random:
        stmt = stmt.order_by(func.random())
    else:
        stmt = stmt.order_by(Question.id.desc())
    stmt = stmt.limit(limit)

    rows = db.scalars(stmt).all()
    return [
        {
            "id": q.id,
            "unit": q.unit,
            "content": q.content,
            "abc": q.abc,
            "options": json.loads(q.options_json or "[]"),
            "image_urls": json.loads(q.image_urls_json or "[]"),
        }
        for q in rows
    ]

