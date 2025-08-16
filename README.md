# GeoMemo Backend

FastAPI 기반 소셜 메모 서비스의 백엔드 프로젝트입니다.  
JWT 기반 인증, 회원가입/로그인, 프로필 관리, 팔로우 기능 등을 제공합니다.

---

## 📂 프로젝트 디렉토리 구조

```
.
├── api/                # 라우터 (엔드포인트)
├── core/               # 보안, JWT, 설정 등 핵심 모듈
├── crud/               # DB CRUD 로직
├── db/                 # 데이터베이스 연결 및 초기화
├── models/             # SQLAlchemy 모델 정의
├── schemas/            # Pydantic 스키마 정의
├── tests/              # 테스트 코드
├── main.py             # FastAPI 앱 진입점
└── requirements.txt    # 의존성 패키지
```

---

## ⚙️ 로컬 환경 설정 및 실행 방법

### 1. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```
Anaconda 등을 사용하셔도 무방합니다.
### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 루트에 생성하고 다음 항목을 작성합니다.
```env
SECRET_KEY= (JWT 토큰 발급용 시크릿 키)
DATABASE_URL=mysql+pymysql://admin:host:port/geomemo
SMTP_USER= (SMTP 계정명)
SMTP_PASS= (SMTP 비밀번호)
SMTP_HOST= (SMTP 호스트)
SMTP_PORT= (SMTP 포트)
AMQP_URL= (AI 서버 연결용 MQ URL)

# ----- Queue names -----
# 1) 감정분석: Backend -> AI (응답은 DB로만 기록, 큐 응답 없음)
EMOTION_REQ_QUEUE=emotion.req

# 2) 인사이트: Backend -> AI (응답은 DB로만 기록, 큐 응답 없음)
INSIGHT_REQ_QUEUE=insight.req

# 3) 장소추천: Backend -> AI -> Backend (응답 큐로 회신)
RECO_REQ_QUEUE=reco.req
RECO_RES_QUEUE=reco.res

# ----- Consumer tuning (prefetch) -----
EMOTION_PREFETCH=16
INSIGHT_PREFETCH=16
RECO_PREFETCH=8

# ----- (선택) 큐 타입 & TTL -----
# Amazon MQ가 지원하면 quorum 권장(복제/HA). 미지원이면 주석 처리하거나 classic 사용
MQ_QUEUE_TYPE=quorum

# 메시지 유효시간(밀리초). 만료 시 DLQ로 이동하도록 RabbitMQ 정책을 함께 구성하세요.
# 필요 없으면 주석 처리
EMOTION_TTL_MS=600000     # 10분
INSIGHT_TTL_MS=900000     # 15분
RECO_TTL_MS=300000        # 5분
```

### 4. DDL
```bash
CREATE TABLE `UserEntity` (
`user_id` INT NOT NULL AUTO_INCREMENT,

follower_count INT DEFAULT 0,

following_count INT DEFAULT 0,
`email` VARCHAR(100) NULL,
`password` VARCHAR(256) NULL,
`name` VARCHAR(10) NULL,
`nickname` VARCHAR(10) NULL,
`phone` VARCHAR(11) NULL,
`profile_image_url` VARCHAR(512) NULL,
`view_settings` VARCHAR(10) NOT NULL DEFAULT 'all',
`privacy_settings` VARCHAR(10) NOT NULL DEFAULT 'open',
`createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
`updatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (`user_id`)
);

CREATE TABLE `LocationEntity` (
`location_id` INT NOT NULL AUTO_INCREMENT,
`name` VARCHAR(20) NULL,
`latitude` DOUBLE NULL,
`longitude` DOUBLE NULL,
`address` VARCHAR(40) NULL,
`category` VARCHAR(30) NULL,
`createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (`location_id`)
);

CREATE TABLE `MemoEntity` (
`memo_id` INT NOT NULL AUTO_INCREMENT,

title VARCHAR(40) NOT NULL, 
`content` TEXT NULL,
`createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
`updatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
`is_public` BOOLEAN NULL,
`user_id` INT NOT NULL,
`location_id` INT NULL,
PRIMARY KEY (`memo_id`)
);

CREATE TABLE `PhotoEntity` (
`photo_id` INT NOT NULL AUTO_INCREMENT,
`photo_url` VARCHAR(255) NULL,
`createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
`updatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
`memo_id` INT NOT NULL,
PRIMARY KEY (`photo_id`)
);

CREATE TABLE `EmotionEntity` (
`emotion_id` INT NOT NULL AUTO_INCREMENT,
`emotion_score` FLOAT NULL,
`emotion_label` VARCHAR(10) NULL,
`memo_id` INT NOT NULL,
PRIMARY KEY (`emotion_id`)
);

CREATE TABLE `MemoScrapEntity` (
`scrap_id` INT NOT NULL AUTO_INCREMENT,
`createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
`user_id` INT NOT NULL,
`memo_id` INT NOT NULL,
PRIMARY KEY (`scrap_id`)
);

CREATE TABLE InsightEntity (
insight_id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT NOT NULL,
content TEXT NULL,
status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
createdAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE `EmailVerifyEntity` (
`verify_id` INT NOT NULL AUTO_INCREMENT,
`user_id` INT NOT NULL,
`verification_code` INT NULL,
`is_verified` BOOLEAN NULL,
`requested_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
`verified_at` DATETIME NULL,
PRIMARY KEY (`verify_id`)
);

CREATE TABLE `FollowEntity` (
`follower_id` INT NOT NULL,
`following_id` INT NOT NULL,
`is_approved` BOOLEAN NOT NULL DEFAULT FALSE,
`createdAt` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
`updatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (`follower_id`, `following_id`)
);

ALTER TABLE `MemoEntity`
ADD CONSTRAINT `FK_UserEntity_TO_MemoEntity_1`
FOREIGN KEY (`user_id`) REFERENCES `UserEntity` (`user_id`) ON DELETE CASCADE;

ALTER TABLE `MemoEntity`
ADD CONSTRAINT `fk_memo_location`
FOREIGN KEY (`location_id`) REFERENCES `LocationEntity` (`location_id`);

ALTER TABLE `PhotoEntity`
ADD CONSTRAINT `FK_MemoEntity_TO_PhotoEntity_1`
FOREIGN KEY (`memo_id`) REFERENCES `MemoEntity` (`memo_id`) ON DELETE CASCADE;

ALTER TABLE `EmotionEntity`
ADD CONSTRAINT `FK_MemoEntity_TO_EmotionEntity_1`
FOREIGN KEY (`memo_id`) REFERENCES `MemoEntity` (`memo_id`) ON DELETE CASCADE;

ALTER TABLE `MemoScrapEntity`
ADD CONSTRAINT `FK_UserEntity_TO_MemoScrapEntity_1`
FOREIGN KEY (`user_id`) REFERENCES `UserEntity` (`user_id`) ON DELETE CASCADE;

ALTER TABLE `MemoScrapEntity`
ADD CONSTRAINT `FK_MemoEntity_TO_MemoScrapEntity_1`
FOREIGN KEY (`memo_id`) REFERENCES `MemoEntity` (`memo_id`) ON DELETE CASCADE;

ALTER TABLE `InsightEntity`
ADD CONSTRAINT `FK_UserEntity_TO_InsightEntity_1`
FOREIGN KEY (`user_id`) REFERENCES `UserEntity` (`user_id`) ON DELETE CASCADE;

ALTER TABLE `EmailVerifyEntity`
ADD CONSTRAINT `FK_UserEntity_TO_EmailVerifyEntity_1`
FOREIGN KEY (`user_id`) REFERENCES `UserEntity` (`user_id`) ON DELETE CASCADE;

ALTER TABLE `FollowEntity`
ADD CONSTRAINT `FK_FOLLOW_FOLLOWER`
FOREIGN KEY (`follower_id`) REFERENCES `UserEntity` (`user_id`) ON DELETE CASCADE;

ALTER TABLE `FollowEntity`
ADD CONSTRAINT `FK_FOLLOW_FOLLOWING`
FOREIGN KEY (`following_id`) REFERENCES `UserEntity` (`user_id`) ON DELETE CASCADE;
```

### 5. 서버 실행
```bash
uvicorn main:app --reload
```

서버는 기본적으로 http://127.0.0.1:8000 에서 실행됩니다.  
API 문서는 자동으로 `/docs` (Swagger UI) 또는 `/redoc` 에서 확인 가능합니다.

---

## 📡 주요 API 엔드포인트

### 인증/회원
- `POST /api/auth/signup` : 회원가입
- `POST /api/auth/login` : 로그인(JWT 발급)
- `POST /api/auth/send-mail` : 이메일 인증 메일 발송

### 사용자
- `GET /api/user/me` : 내 정보 조회
- `POST /api/user/update-view` : 보기 설정 변경  
  (`all` / `follows` / `self`)
- `POST /api/user/profile-image` : 프로필 이미지 업로드/변경

### 팔로우
- `POST /api/follow/{user_id}` : 팔로우 요청
- `DELETE /api/follow/{user_id}` : 언팔로우
- `GET /api/follow/followings` : 내가 팔로우 중인 목록
- `GET /api/follow/followers` : 나를 팔로우 중인 목록

---

## 📑 전체 API 명세
상세한 엔드포인트와 요청/응답 구조는 **[Notion API 명세 문서](https://yoonsubport.notion.site/API-222cc0f4e33481158673c25608b6644b?source=copy_link)** 에 정리되어 있습니다.
