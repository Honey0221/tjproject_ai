from pydantic import BaseModel
from typing import Optional, List

# -----------------------------------------------------------------------------
# ✅ [1] 최근 뉴스 크롤링 + 감정 분석 요청 모델
# - 프론트에서 키워드만 입력하면 최신 뉴스 5건을 수집하고 감정 분석
# - 모델: "vote", "stack", "transformer" 중 하나 선택 가능
# -----------------------------------------------------------------------------
class NewsAnalysisRequest(BaseModel):
    keyword: str                            # 검색 키워드 (필수)
    max_articles: Optional[int] = 5         # 수집할 뉴스 개수
    model: Optional[str] = "vote"           # 사용할 감정 분석 모델
    headless: Optional[bool] = True         # 크롬 드라이버 헤드리스 여부


# -----------------------------------------------------------------------------
# ✅ [2] 필터 기반 뉴스 분석 요청 모델
# - 통합분류 / 사건사고분류 / 날짜 필터를 기반으로 뉴스 수집
# - 감정 분석까지 포함 (기존 analyzeNews/filter API 사용)
# -----------------------------------------------------------------------------
class FilteredNewsAnalysisRequest(BaseModel):
    keyword: str
    unified_category: Optional[List[str]] = None   # 통합분류 (e.g., "정치", "경제")
    incident_category: Optional[List[str]] = None  # 사건사고분류 (e.g., "범죄", "재해")
    start_date: Optional[str] = None               # 시작일 (manual 모드일 때)
    end_date: Optional[str] = None                 # 종료일 (manual 모드일 때)
    period_label: Optional[str] = None             # preset 모드일 때 선택한 기간 키 (예: "date1-7")
    date_method: Optional[str] = "manual"          # 날짜 방식: "manual" 또는 "preset"
    max_articles: Optional[int] = 100              # 수집할 뉴스 최대 개수
    model: Optional[str] = "vote"                  # 감정 분석 모델
    headless: Optional[bool] = True


# -----------------------------------------------------------------------------
# ✅ [3] 배치 수집용 요청 모델 (감정 분석 없이 뉴스 수집만)
# - 주로 관리자/백오피스 용도로 사용
# -----------------------------------------------------------------------------
class BatchRequest(BaseModel):
    keyword: str
    unified_category: Optional[List[str]] = None
    incident_category: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date_method: Optional[str] = "manual"
    period_label: Optional[str] = None
    max_articles: Optional[int] = 100
