import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Science Exam Backend"
    app_env: str = "dev"
    app_debug: bool = False

    # Render / Railway 환경변수에 DATABASE_URL만 넣으면 동작
    database_url: str = "sqlite:///./local.db"

    # 외부 회원 검증 API (선택)
    member_check_api_url: str | None = None
    member_check_api_key: str | None = None

    # Aligo 문자 API (선택)
    aligo_api_key: str | None = None
    aligo_user_id: str | None = None
    aligo_sender: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def _normalize_database_url(url: str) -> str:
    # 일부 서비스는 postgres:// 를 내려주므로 SQLAlchemy용으로 변환
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Render PostgreSQL(특히 외부 URL)은 SSL 미설정 시 기동 중 DB 접속이 실패하는 경우가 많음
    if (
        url.startswith("postgresql+psycopg")
        and "sslmode=" not in url
        and os.environ.get("RENDER") == "true"
    ):
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


settings = Settings()
settings.database_url = _normalize_database_url(settings.database_url)

