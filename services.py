import json
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from core_config import settings
from models import Question, User
from pdf_parse import extract_pdf


def check_member_via_external_api(name: str, phone: str) -> bool:
    """
    외부 회원 API 연동 포인트.
    - 환경변수(member_check_api_url)가 없으면 개발 편의상 True 반환
    """
    if not settings.member_check_api_url:
        return True

    headers = {}
    if settings.member_check_api_key:
        headers["Authorization"] = f"Bearer {settings.member_check_api_key}"

    payload = {"name": name, "phone": phone}
    try:
        resp = requests.post(
            settings.member_check_api_url,
            json=payload,
            headers=headers,
            timeout=8,
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return bool(data.get("is_member", False))
    except Exception:
        # 외부 API 장애 시 False 처리(보수적)
        return False


def get_or_create_user(db: Session, name: str, phone: str, is_member: bool) -> User:
    existing = db.scalar(select(User).where(User.phone == phone))
    if existing:
        existing.name = name
        existing.is_verified_member = is_member
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    user = User(name=name, phone=phone, is_verified_member=is_member)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def upsert_questions_from_pdf(db: Session, pdf_path: str, source_file: str) -> int:
    items = extract_pdf(pdf_path)
    count = 0
    for item in items:
        qid = str(item["id"])
        q = db.get(Question, qid)
        if q is None:
            q = Question(id=qid)
        q.unit = str(item.get("unit") or "")
        q.content = item.get("content") or ""
        q.abc = item.get("abc") or ""
        q.options_json = json.dumps(item.get("options") or [], ensure_ascii=False)
        q.image_urls_json = json.dumps(item.get("image_urls") or [], ensure_ascii=False)
        q.source_file = source_file
        db.add(q)
        count += 1
    db.commit()
    return count

