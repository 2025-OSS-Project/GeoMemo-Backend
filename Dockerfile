# syntax=docker/dockerfile:1.4
# 1) 빌드 스테이지: 의존성 설치
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app

# requirements.txt만 복사하여 레이어 캐싱
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) 런타임 스테이지: 코드 및 패키지 복사
FROM python:3.12-slim-bookworm
WORKDIR /app

# 빌드 스테이지에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# 애플리케이션 코드 복사
COPY . .

# 기본 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
