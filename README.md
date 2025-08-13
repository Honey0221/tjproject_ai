# TJ Project AI - 기업 분석 플랫폼

## 📋 소개

TJ Project AI는 기업 정보 수집, 리뷰 분석, 감정 분석, 뉴스 키워드 추출 등을 제공하는 종합적인 기업 분석 플랫폼의 백엔드입니다. FastAPI 기반의 API로 구성되어 있습니다.

## 🚀 주요 기능

### 🏢 기업 분석
- **기업 검색**: 기업명 또는 카테고리별 검색
- **재무 랭킹**: 매출액, 영업이익, 순이익 기준 기업 랭킹
- **자동 크롤링**: Wikipedia, TeamBlind, BigKinds에서 기업 및 뉴스 정보 자동 수집
- **Redis 캐싱**: 검색 결과 캐싱으로 성능 최적화

### 📊 기업 리뷰 분석
- **감정 분석**: KoELECTRA 기반 한국어 감정 분석
- **키워드 추출**: 리뷰에서 핵심 키워드 자동 추출
- **통계 분석**: 긍정/부정/중립 비율 분석
- **캐시 시스템**: 분석 결과 캐싱으로 빠른 응답

### 🤖 뉴스 감정 분석
- **뉴스 크롤링**: BigKinds API 연동 뉴스 수집
- **실시간 분석**: 텍스트 입력 시 즉시 감정 분석 결과 제공
- **앙상블 모델**: LightGBM, RandomForest, SVM, XGBoost 등 다중 모델
- **BERT 모델**: KcBERT 기반 한국어 특화 감정 분석
- **감정 분석**: 뉴스 기사의 감정 톤 분석
- **키워드 추출**: 뉴스 기사에서 핵심 키워드 추출

### 💬 챗봇 & 문의
- **기업 검색 챗봇**: 자연어로 기업 정보 조회
- **뉴스 검색**: 특정 키워드 관련 뉴스 검색
- **문의 시스템**: 사용자 문의사항 관리

## 🛠️ 기술 스택

### 백엔드
- **웹 프레임워크**: FastAPI 0.116.1
- **데이터베이스**: 
  - MongoDB (기업 데이터)
  - Redis (캐싱)
  - PostgreSQL (사용자 데이터)
- **AI/ML**: 
  - PyTorch 2.7.1
  - Transformers 4.53.2
  - Scikit-learn 1.3.2
  - XGBoost, LightGBM
- **자연어 처리**:
  - KoNLPy 0.6.0
  - Sentence-Transformers 3.3.1
  - KeyBERT 0.9.0
- **웹 크롤링**: Selenium 4.34.2, BeautifulSoup4

## 📁 주요 디렉토리 구조

### 백엔드 (`django/`)
```
app/
├── routers/           # API 엔드포인트
│   ├── company.py     # 기업 검색/랭킹 API
│   ├── review.py      # 리뷰 분석 API
│   ├── emotion.py     # 감정 분석 API
│   ├── news.py        # 뉴스 분석 API
│   └── chatbot.py     # 챗봇 API
├── services/          # 비즈니스 로직
├── models/           # 데이터 모델
├── database/         # 데이터베이스 연결
└── utils/           # 유틸리티 함수

crawling/
├── com_crawling.py           # 기업 정보 크롤링
├── com_review_crawling.py    # 기업 리뷰 크롤링
├── latest_news_crawling.py   # 최신 뉴스 크롤링
└── bigKinds_crawling_speed.py # BigKinds API 크롤링

emotionAnalysisModels/
├── baseEnsembleModels/       # 앙상블 ML 모델들
├── emotionKcbertModels/      # KcBERT 모델
├── emotionData/             # 학습 데이터
└── emotionPredictModel.py   # 감정 예측 모델
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
POSTGRES_DB=tjproject
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# 캐시 설정 (초)
CACHE_EXPIRE_TIME=7200
RANKING_CACHE_EXPIRE_TIME=3600
REVIEW_ANALYSIS_CACHE_EXPIRE_TIME=7200

# CORS 설정
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ALLOW_CREDENTIALS=true
```

3. **서버 실행**
```bash
python run_fastapi.py
```

## 📡 API 엔드포인트

### 기업 관련
- `GET /api/companies/search` - 기업 검색
- `GET /api/companies/ranking` - 기업 재무 랭킹
- `GET /api/companies/cache/stats` - 캐시 통계
- `DELETE /api/companies/cache/clear` - 캐시 초기화

### 리뷰 분석
- `POST /api/reviews/analyze` - 리뷰 분석 실행
- `GET /api/reviews/cache/stats` - 리뷰 캐시 통계
- `DELETE /api/reviews/cache/clear` - 리뷰 캐시 초기화

### 감정 분석
- `POST /api/emotion/api/emotion` - 텍스트 감정 분석

### 뉴스 분석
- `POST /api/news/latest` - 최신 뉴스 크롤링
- `GET /api/news/latest/all` - 모든 뉴스 조회
- `POST /api/news/keywords` - 뉴스 키워드 추출

### 분석 서비스
- `POST /api/analyze` - 뉴스 분석
- `POST /api/analyze/filter` - 필터링된 뉴스 분석
- `POST /api/analyze/batch` - 배치 분석

### 시스템
- `GET /` - API 상태 확인
- `GET /docs` - Swagger UI
- `GET /cache` - 전체 캐시 통계
- `DELETE /cache/clear` - 전체 캐시 초기화

## 🤖 AI 모델 정보

### 감정 분석 모델
1. **KcBERT 모델**: 한국어 특화 BERT 모델
2. **앙상블 모델**: 
   - LightGBM
   - Random Forest
   - SVM
   - XGBoost
   - Logistic Regression

### 리뷰 분석 모델
- **KoELECTRA**: `Copycats/koelectra-base-v3-generalized-sentiment-analysis`
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