"""SQLite 저장소: 통합과학 문제 (id, unit, content, abc, options)."""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "quiz.db"


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            unit TEXT NOT NULL,
            content TEXT,
            abc TEXT,
            options_json TEXT NOT NULL,
            image_paths TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def upsert_question(
    qid: str,
    unit: str,
    content: str,
    abc: str,
    options: list[str],
    image_paths: list[str] | None = None,
):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO questions (id, unit, content, abc, options_json, image_paths)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            unit = excluded.unit,
            content = excluded.content,
            abc = excluded.abc,
            options_json = excluded.options_json,
            image_paths = excluded.image_paths
        """,
        (
            qid,
            unit,
            content,
            abc,
            json.dumps(options, ensure_ascii=False),
            json.dumps(image_paths or [], ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def get_by_id(qid: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, unit, content, abc, options_json, image_paths FROM questions WHERE id = ?",
        (qid,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "unit": row[1],
        "content": row[2] or "",
        "abc": row[3] or "",
        "options": json.loads(row[4]),
        "image_urls": json.loads(row[5]) if row[5] else [],
    }


def count_questions() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    conn.close()
    return n


def import_json_file(path: Path) -> int:
    """기존 quiz_database.json 호환: unit이 숫자일 수 있음."""
    from pdf_parse import _parse_options_block

    if not path.is_file():
        return 0
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    n = 0
    for item in data:
        qid = str(item["id"])
        unit = item.get("unit")
        if isinstance(unit, int):
            unit = str(unit)
        else:
            unit = str(unit or "")
        content = item.get("content") or ""
        abc = item.get("abc") or ""
        opts = item.get("options") or []
        if len(opts) == 1 and isinstance(opts[0], str) and "\u2460" in opts[0]:
            opts = _parse_options_block(opts[0])
        elif len(opts) < 5:
            opts = list(opts) + [""] * (5 - len(opts))
        else:
            opts = opts[:5]
        if not abc and "보기" in content:
            parts = content.rsplit("보기", 1)
            content = parts[0].strip()
            abc = "보기" + parts[1].strip() if len(parts) > 1 else ""
        imgs = item.get("image_urls") or []
        upsert_question(qid, unit, content, abc, opts, imgs)
        n += 1
    return n
