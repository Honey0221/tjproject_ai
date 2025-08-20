# 기업 여론 분석 시스템(COPS)

## 📋 소개

COPS는 기업 정보 수집, 리뷰 분석, 감정 분석, 뉴스 키워드 추출 등을 제공하는 종합적인 기업 분석 플랫폼의 백엔드입니다. FastAPI 기반의 API로 구성되어 있습니다.

## 🚀 담당 주요 기능

### 🏢 기업 분석
- **기업 검색**: 기업명 또는 카테고리별 검색
- **재무 랭킹**: 매출액, 영업이익, 순이익 기준 기업 랭킹
- **자동 크롤링**: Wikipedia, TeamBlind에서 기업 및 리뷰 정보 자동 수집
- **Redis 캐싱**: 검색 결과 캐싱으로 성능 최적화

### 📊 기업 리뷰 분석
- **감정 분석**: KoELECTRA 기반 한국어 감정 특화로 파인튜닝한 모델로 분석 실행
- **키워드 추출**: Okt를 활용한 핵심 키워드 자동 추출
- **통계 분석**: 긍정/부정 감정 비율 분석
- **캐시 시스템**: 분석 결과 캐싱으로 빠른 응답 속도

### 💬 챗봇 기능
- **개발 의도**: 메인 서비스를 보조하는 역할
- **서비스 소개**: 정적인 기능으로 서비스 간략 소개
- **기업 및 뉴스 검색**: 기업 이름 검색 후 정보 조회
- **문의 시스템**: 사용자 피드백을 위한 문의사항 작성 기능

## 🛠️ 기술 스택

### 백엔드
- **웹 프레임워크**: FastAPI 0.116.1
- **데이터베이스**: 
  - MongoDB (기업 정보 & 회원 리뷰)
  - PostgreSQL (회원 문의)
  - Redis (캐싱)
- **자연어 처리**:
  - KoNLPy 0.6.0
- **웹 크롤링**: Selenium 4.34.2

## 📁 프로젝트 구조

```
django/
├── app/                          
│   ├── main.py                   # FastAPI 애플리케이션 진입점
│   ├── config.py                 # 환경 설정
│   ├── database/                 # 데이터베이스 연결 관리
│   │   ├── __init__.py
│   │   ├── mongodb.py            # MongoDB 연결
│   │   ├── postgres.py           # PostgreSQL 연결
│   │   └── redis_client.py       # Redis 클라이언트
│   ├── models/                   # 데이터 모델
│   │   ├── company.py            
│   │   └── inquiry.py            
│   ├── routers/                  # API 엔드포인트    
│   │   ├── chatbot.py         
│   │   ├── company.py           
│   │   ├── inquiry.py               
│   │   ├── review.py             
│   │   ├── system.py            
│   │   └── user_review.py       
│   ├── schemas/                  # Pydantic 스키마
│   │   ├── chatbot_schema.py
│   │   ├── common_schema.py
│   │   ├── company_schema.py
│   │   ├── review_analysis_schema.py
│   │   └── user_review_schema.py
│   ├── services/                 
│   │   ├── review_analysis_service.py # 리뷰 분석 서비스
│   │   ├── search_service.py     # 기업 검색 서비스
│   │   └── user_review_service.py # 회원 리뷰 서비스
├── crawling/                     
│   ├── com_crawling.py               # 기업 정보 크롤링
│   ├── com_review_crawling.py        # 기업 리뷰 크롤링
│   └── driver.py                     # 크롤링 드라이버 관리
├── machine_model/                # 리뷰 분석 모델
│   └── company_review/
│       ├── review_analyzer.py    # 리뷰 분석기
│       └── review_dataset.py     # 리뷰 데이터셋
├── tests/                        # 테스트 파일
│   ├── test_company_review.py
│   └── test_company_search.py
├── requirements.txt              # Python 의존성
└── run_fastapi.py               # 서버 실행 스크립트
```

## 🔧 설치 및 실행

### 환경 요구사항
- Python 3.9+
- Node.js 16+
- MongoDB
- Redis
- PostgreSQL

### 백엔드 설정

1. **의존성 설치**
```bash
cd django
pip install -r requirements.txt
```

2. **환경 변수 설정** (`.env` 파일 생성)
```env
# 데이터베이스 설정
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=company_db

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=[your_DB]
POSTGRES_USER=[your_user]
POSTGRES_PASSWORD=[your_password]

# 캐시 설정 (초)
CACHE_EXPIRE_TIME=7200
RANKING_CACHE_EXPIRE_TIME=3600
REVIEW_ANALYSIS_CACHE_EXPIRE_TIME=7200

# CORS 설정
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ALLOW_CREDENTIALS=true
```

3. **서버 실행**
```
python run_fastapi.py
uvicorn app.main:app --reload
```

## 📡 API 엔드포인트

### 기업 관련
- `GET /api/companies/search` - 기업 검색
- `GET /api/companies/ranking` - 기업 재무 랭킹

### 리뷰 분석
- `POST /api/reviews/analyze` - 리뷰 분석 실행
- `GET /api/reviews/cache/stats` - 리뷰 캐시 통계

### 시스템
- `GET /` - API 상태 확인
- `GET /docs` - Swagger UI
- `GET /cache` - 전체 캐시 통계
- `DELETE /cache/clear` - 전체 캐시 초기화

## 🤖 AI 모델 정보

### 리뷰 분석 모델
- **KoELECTRA 모델**: `Copycats/koelectra-base-v3-generalized-sentiment-analysis`
- **모델 특징**: KOELECTRA의 감정 분석이 특화되도록 파인 튜닝한 모델
- **키워드 추출**: KeyBERT 기반

## 📈 성능 최적화

1. **Redis 캐싱**: 반복 요청 최적화
2. **비동기 처리**: FastAPI 비동기 지원
3. **연결 풀링**: 데이터베이스 연결 최적화
4. **모델 재사용**: AI 모델 인스턴스 캐싱

## 📊 모니터링

### 캐시 통계 API
- 전체 캐시 시스템 상태 모니터링
- 각 캐시 유형별 키 개수 추적
- 캐시 히트율 분석 가능

### 로깅 시스템
- 캐시 히트/미스 로깅
- 데이터베이스 연결 상태 로깅
- 크롤링 작업 진행 상황 로깅

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 📞 연락처

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요.

---
