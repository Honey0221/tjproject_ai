from fastapi import APIRouter

# 📦 요청 바디 스키마 (Pydantic) 정의
from ..schemas.analyze_schema import (
    NewsAnalysisRequest,
    FilteredNewsAnalysisRequest,
    BatchRequest
)

# 🧠 실제 처리 로직을 담은 서비스 함수
from ..services.analyze_service import (
    analyze_news,
    analyze_news_filtered,
    emotion_batch
)

# 📍 API 라우터 객체 생성
router = APIRouter(prefix="/analyzeNews", tags=["analyzeNews"])


# -----------------------------------------------------------------------------
# ✅ 엔드포인트 1: 최신 뉴스 크롤링 후 감정 분석
# - 최근 뉴스 요약을 수집한 뒤, 감정 분석을 수행
# - 예: "하이브"라는 키워드로 최근 5건의 뉴스에서 긍/부정/중립 분석
# -----------------------------------------------------------------------------
@router.post("/")
def analyze_news_route(req: NewsAnalysisRequest):
    return analyze_news(req)


# -----------------------------------------------------------------------------
# ✅ 엔드포인트 2: 날짜 + 분류 필터를 적용한 뉴스 분석
# - 통합/사건사고 카테고리, 날짜 범위 등을 사용하여 뉴스 수집 후 감정 분석
# - 사용자가 지정한 필터 조건에 따라 기사들을 수집하고 분석
# -----------------------------------------------------------------------------
@router.post("/filter")
def analyze_news_filtered_route(req: FilteredNewsAnalysisRequest):
    return analyze_news_filtered(req)


# -----------------------------------------------------------------------------
# ✅ 엔드포인트 3: 감정 분석 없이 뉴스 수집만 수행 (배치 수집용)
# - 크롤링 결과를 저장하거나 후처리를 위한 용도로 사용
# - 감정 모델을 사용하지 않음
# -----------------------------------------------------------------------------
@router.post("/batch")
def batch_analysis_route(req: BatchRequest):
    return emotion_batch(req)
