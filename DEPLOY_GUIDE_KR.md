# FastAPI 백엔드 초보자 배포 매뉴얼 (GitHub + Render)

이 문서는 지금 폴더(`e:\문서\code`)의 코드를 기준으로,  
**내 PC -> GitHub -> Render 배포**까지 처음 하는 분 기준으로 작성했습니다.

---

## 1) 내 컴퓨터에서 먼저 실행 확인

PowerShell에서:

```powershell
Set-Location "e:\문서\code"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

브라우저에서 아래 확인:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs` (Swagger UI)

---

## 2) GitHub에 코드 올리기

### 2-1. GitHub 저장소 만들기
1. GitHub 로그인
2. 우측 상단 `+` -> `New repository`
3. 저장소 이름 입력 (예: `science-exam-backend`)
4. `Create repository`

### 2-2. 로컬 폴더를 Git 초기화해서 푸시

PowerShell에서:

```powershell
Set-Location "e:\문서\code"
git init
git add .
git commit -m "init: fastapi backend skeleton"
git branch -M main
git remote add origin https://github.com/<내계정>/<저장소이름>.git
git push -u origin main
```

> 이미 git 저장소가 있다면 `git init`/`remote add`는 생략하세요.

---

## 3) Render에서 배포하기

### 3-1. PostgreSQL 생성
1. Render 로그인
2. `New +` -> `PostgreSQL`
3. 이름 생성 후 완료
4. 생성된 DB의 `Internal Database URL` 또는 `External Database URL` 복사

### 3-2. Web Service 생성
1. Render에서 `New +` -> `Web Service`
2. GitHub 저장소 연결
3. 설정:
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command** (권장 순서):
     1. **`python run_server.py`** — `$PORT` 치환 문제 없이 동작
     2. `bash run.sh` — bash에서 `PORT` 사용
     3. `uvicorn main:app --host 0.0.0.0 --port $PORT` — Render 셸에서 `$PORT`가 비면 **지금 같은 오류**가 납니다
   - 대시보드 Start Command를 비우면 `Procfile`의 `web: python run_server.py`가 쓰일 수 있습니다(설정에 따라 다름).

### 3-3. 환경변수 설정
Render 서비스의 `Environment`에서 아래 추가:

- `DATABASE_URL` = (Render PostgreSQL URL)
- 필요 시:
  - `MEMBER_CHECK_API_URL`
  - `MEMBER_CHECK_API_KEY`
  - `ALIGO_API_KEY`
  - `ALIGO_USER_ID`
  - `ALIGO_SENDER`

배포가 끝나면 서비스 URL에서:
- `/health`
- `/docs`
확인

---

## 4) Railway로 배포하고 싶다면 (간단 버전)

1. Railway 프로젝트 생성
2. GitHub 저장소 연결
3. PostgreSQL 플러그인 추가
4. `DATABASE_URL` 환경변수 연결 확인
5. Start command를 아래로 설정:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 5) 배포 후 테스트 순서

1. `GET /health`
2. `POST /admin/import-pdf` 로 PDF 업로드
3. `GET /questions?limit=5`
4. `POST /auth/check-member`

Swagger(`/docs`)에서 바로 테스트 가능합니다.

---

## 6) 자주 막히는 문제

- `ModuleNotFoundError`: `requirements.txt` 누락 패키지 확인
- DB 연결 오류: `DATABASE_URL` 값 오타/권한 문제 확인
- 업로드 실패: `python-multipart` 설치 여부 확인
- 한글 깨짐: DB/파일 인코딩 UTF-8 유지

---

## 7) 다음 단계 권장

1. Alembic 마이그레이션 도입 (운영 DB 스키마 안전 관리)
2. 관리자 인증(JWT) 추가 (`/admin/import-pdf` 보호)
3. 시험/채점 API 확장
4. Aligo 문자 발송 모듈 연결 및 실패 재시도 큐 구성

