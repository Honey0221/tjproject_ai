from typing import Optional, List, Literal
from pydantic import BaseModel, Field, BaseModel

# -----------------------------------------------------------------------------
# ✅ 최신 뉴스 실시간 크롤링 요청 모델
# - 사용자가 키워드를 입력하면 BigKinds에서 관련 뉴스 5건 실시간 수집
# - 주로 "/api/news/latest" 라우트에 사용됨
# -----------------------------------------------------------------------------
class LatestNewsRequest(BaseModel):
    keyword: str                        # 검색 키워드 (필수)
    headless: Optional[bool] = True    # 크롬 브라우저 헤드리스 실행 여부 (기본값 True)


# -----------------------------------------------------------------------------
# ✅ 키워드 추출 요청 모델 (뉴스 필터 기반 크롤링 후 키워드 뽑기)
# - 감정 분석 없이 summary 기준으로 핵심어를 추출
# - 통합/사건사고 분류 + 날짜 방식 필터 사용 가능
# - "/api/news/keywords" 라우트에 사용됨

# 키워드추출모델리스트
# "method": "tfidf"         // ✔ TF-IDF 기반
# "method": "krwordrank"    // ✔ KRWordRank 기반
# "method": "lda"           // ✔ LDA 토픽 모델링
# "method": "okt"           // ✔ 형태소 분석 + 명사 빈도
# -----------------------------------------------------------------------------


class KeywordExtractionRequest(BaseModel):
    keyword: str
    unified_category: Optional[List[str]] = None
    incident_category: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date_method: Optional[str] = "manual"
    period_label: Optional[str] = None
    max_articles: Optional[int] = 100
    headless: Optional[bool] = True
    top_n: Optional[int] = 10
    method: Literal["tfidf", "krwordrank", "lda", "okt", "keybert"] = "tfidf"  # ✅ 제한 추가
    aggregate_from_individual: Optional[bool] = False  #

