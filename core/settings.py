import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_dev_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# SMTP 설정
SMTP_USER = os.getenv("SMTP_USER")          # 예: yourname@gmail.com
SMTP_PASS = os.getenv("SMTP_PASS")          # 예: 앱 비밀번호
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
