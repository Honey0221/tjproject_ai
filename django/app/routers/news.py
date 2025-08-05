import os, json
from fastapi import APIRouter, HTTPException
from app.schemas.news_schema import LatestNewsRequest, KeywordExtractionRequest
from app.services.news_service import crawl_and_extract_keywords_with_cache
from app.services.news_service import crawl_latest_articles_db

# 기본 접두사와 Swagger 태그 지정
router = APIRouter(
    prefix="/news",   # 실제 경로: /api/news/...
    tags=["news"]     # Swagger UI 태그
)

# -----------------------------------------------------------------------------
# ✅ [1] 최신 뉴스 크롤링 (실시간 수집)
# - 키워드를 기반으로 BigKinds에서 실시간 뉴스 수집
# - 프론트 검색창 연동 용도
# -----------------------------------------------------------------------------

@router.post("/latest")
def latest_news(req: LatestNewsRequest):
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")

    try:
        articles = crawl_latest_articles_db(keyword=keyword, headless=req.headless)
        return {
            "keyword": keyword,
            "count": len(articles),
            "articles": articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# ✅ [2] 저장된 크롤링 결과 중 가장 최신 JSON 불러오기
# - newsCrawlingData/ 폴더에서 가장 최근 파일을 열어 상위 5개 기사 반환
# - 서버 재시작 없이도 저장된 결과 확인 가능
# -----------------------------------------------------------------------------
@router.get("/latest/all")
def latest_all_news():
    DATA_DIR = os.path.join(os.getcwd(), "newsCrawlingData")

    try:
        json_files = sorted(
            [f for f in os.listdir(DATA_DIR) if f.endswith(".json")],
            key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
            reverse=True
        )

        if not json_files:
            raise HTTPException(status_code=404, detail="크롤링된 뉴스 파일이 없습니다.")

        latest_file = os.path.join(DATA_DIR, json_files[0])
        with open(latest_file, "r", encoding="utf-8") as f:
            articles = json.load(f)

        return articles[:5]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# ✅ [3] 키워드 기반 뉴스 키워드 추출 (감정분석 X)
# - 뉴스 수집 조건은 /api/analyzeNews/filter와 동일
# - 모델을 사용하지 않고, summary 기준 키워드 추출 (KeyBERT)
# - 개별 기사 키워드 + 전체 통합 키워드 제공
# -----------------------------------------------------------------------------
@router.post("/keywords")
async def extract_keywords(req: KeywordExtractionRequest):
    if not req.keyword.strip():
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")

    try:
        # 기존: result = crawl_and_extract_keywords(req)
        result = await crawl_and_extract_keywords_with_cache(req)  # ✅ 캐시 적용
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"키워드 추출 중 오류 발생: {str(e)}")
