"""
Render 등에서 셸의 $PORT 치환이 비어 버리는 경우를 피하기 위해
환경변수 PORT를 Python에서 직접 읽습니다.
"""
import os

import uvicorn

if __name__ == "__main__":
    port_raw = os.environ.get("PORT")
    if not port_raw:
        raise SystemExit(
            "PORT 환경변수가 없습니다. Render Web Service에서 자동으로 설정됩니다. "
            "서비스 유형이 Web Service인지 확인하세요."
        )
    port = int(port_raw)
    uvicorn.run("main:app", host="0.0.0.0", port=port)
