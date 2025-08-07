import os
import json
from crawling.latest_news_crawling import get_latest_articles
from fastapi import HTTPException
from keybert import KeyBERT
from crawling.bigKinds_crawling_speed import search_bigkinds
from app.database.db.crawling_database import (
    get_articles_by_conditions,
    find_existing_bulk,
    upsert_article,
    ensure_indexes,
    get_articles_by_keyword_recent
)
from app.utils.stopwords import DEFAULT_STOPWORDS
from app.utils.keyword_extractors import (
    extract_with_keybert, extract_with_tfidf, extract_with_krwordrank,
    extract_with_lda, extract_with_okt
)
from app.database.db.crawling_database import save_overall_keywords
from app.utils.news_keywords_cache_utils import get_or_cache, make_redis_key
from app.database.redis_client import redis_client

from app.config import settings
from app.utils.news_keywords_cache_utils import get_or_cache
from app.database.db.crawling_database import db




# ✅ 한국어 SBERT 기반 KeyBERT 모델 초기화
kw_model = KeyBERT(model="jhgan/ko-sbert-nli")

def crawl_latest_articles_db(keyword: str, headless: bool = True):
    """
    ✅ 키워드 기반으로 DB에 저장된 최신 기사 5개 반환
    - 없다면 크롤링 후 저장하고 반환
    """
    keyword = keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")

    # ✅ 최신 기사 5개 조회 (DB)
    articles = get_articles_by_keyword_recent(keyword=keyword, limit=5)

    if articles and len(articles) == 5:
        print(f"✅ [DB 재사용] '{keyword}' 키워드의 최신 기사 5건 반환 (DB에서)")
        return articles

    # ✅ 크롤링 수행
    print(f"🌐 [크롤링 시작] '{keyword}' 키워드로 최신 기사 수집 시도 중...")
    try:
        raw_articles = get_latest_articles(keyword, max_articles=5, headless=headless)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 실패: {str(e)}")

    if not raw_articles:
        raise HTTPException(status_code=404, detail="해당 키워드에 대한 최신 기사가 없습니다.")

    # ✅ 인덱스 보장
    try:
        ensure_indexes()
    except Exception:
        pass

    # ✅ 기존 존재 여부 확인
    keys = [(a.get("title", ""), a.get("date", "")) for a in raw_articles]
    existing_map = find_existing_bulk(keys, model="latest")

    new_count = 0
    reuse_count = 0
    for article in raw_articles:
        title = article.get("title", "")
        date = article.get("date", "")
        key = (title, date)

        if key in existing_map:
            print(f"✅ 이미 존재 (중복 저장 안함): {title}")
            reuse_count += 1
        else:
            print(f"🆕 DB 저장됨 (신규): {title}")
            upsert_article(article, label=None, confidence=None, keyword=keyword, model="latest")
            new_count += 1

    print(f"\n📊 저장 요약: 신규 {new_count}건 | 중복 {reuse_count}건\n")

    return raw_articles



def read_latest_file():
    """
    ✅ 가장 최근 저장된 JSON 파일에서 상위 5개의 기사 반환
    """
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
            data = json.load(f)
            if not data:
                raise HTTPException(status_code=404, detail="최근 뉴스 파일이 비어 있습니다.")
            return data[:5]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 읽기 실패: {str(e)}")

# ✅ 통합된 키워드 추출 서비스 (뉴스 기반 count 및 비중 출력용)

def crawl_and_extract_keywords(req):
    try:
        method = req.method
        top_n = req.top_n or 10
        aggregate_from_individual = getattr(req, "aggregate_from_individual", False)

        # ✅ 무조건 크롤링 → 중복 기사도 summary 보완됨
        articles = search_bigkinds(
            keyword=req.keyword,
            unified_category=req.unified_category,
            incident_category=req.incident_category,
            start_date=req.start_date,
            end_date=req.end_date,
            date_method=req.date_method,
            period_label=req.period_label,
            max_articles=req.max_articles
        )

        if not articles:
            raise HTTPException(status_code=404, detail="뉴스 없음")

        ensure_indexes()

        # ✅ 개별 키워드 추출 + DB 저장
        all_texts = []
        individual_results = []
        total_keyword_sum = 0

        for article in articles:
            summary = article.get("summary", "").strip()
            title = article.get("title", "")

            if not summary:
                continue

            keywords = extract_keywords(summary, method, top_n)
            count = sum(cnt for _, cnt in keywords)
            total_keyword_sum += count

            keyword_items = [
                {
                    "keyword": word,
                    "count": cnt,
                    "ratio": round(cnt / count * 100, 1) if count else 0
                }
                for word, cnt in keywords
            ]

            individual_results.append({
                "title": title,
                "keywords": keyword_items,
                "count": count
            })

            all_texts.append(summary)

            # ✅ 분석된 키워드를 포함해 DB 저장
            upsert_article(
                article=article,
                label=None,
                confidence=None,
                keyword=keyword_items,  # 실제 추출된 키워드
                model="keyword_" + method
            )

        # ✅ 기사별 비중 추가
        for doc in individual_results:
            doc["ratio"] = round(doc["count"] / total_keyword_sum * 100, 1) if total_keyword_sum else 0

        # ✅ 전체 키워드 집계 방식
        if aggregate_from_individual:
            from app.utils.keyword_extractors import aggregate_keywords_from_articles
            formatted_overall = aggregate_keywords_from_articles(individual_results, top_n=top_n)
        else:
            all_corpus = all_texts if method in ["lda", "okt", "tfidf"] else " ".join(all_texts)
            overall_keywords = extract_keywords(all_corpus, method, top_n)
            total_score = sum(cnt for _, cnt in overall_keywords)

            formatted_overall = [
                {
                    "keyword": word,
                    "count": cnt,
                    "ratio": round(cnt / total_score * 100, 1) if total_score else 0
                }
                for word, cnt in overall_keywords
            ]

        # ✅ 분석 결과 저장
        save_overall_keywords(
            keyword=req.keyword,
            method=method,
            overall_keywords=formatted_overall,
            individual_keywords=individual_results,
            start_date=req.start_date,
            end_date=req.end_date,
            unified_category=req.unified_category,
            incident_category=req.incident_category
        )

        return {
            "count": len(articles),
            "individual_keywords": individual_results,
            "overall_keywords": formatted_overall,
            "aggregate_mode": "individual" if aggregate_from_individual else "summary_merged"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))





# ✅ 추출 방식별 공통 처리 함수
def extract_keywords(text_or_list, method, top_n):
    # 모든 방식이 리스트를 기대하는 건 아니므로, 필요한 경우만 처리
    if method in ["tfidf", "okt", "lda"] and isinstance(text_or_list, str):
        text_or_list = [text_or_list]  # ✅ TF-IDF, Okt, LDA는 리스트로 감싸야 함

    if method == "tfidf":
        return extract_with_tfidf(text_or_list, DEFAULT_STOPWORDS, top_n, return_counts=True)
    elif method == "krwordrank":
        return extract_with_krwordrank(text_or_list, DEFAULT_STOPWORDS, top_n, return_counts=True)
    elif method == "okt":
        return extract_with_okt(text_or_list, DEFAULT_STOPWORDS, top_n, return_counts=True)
    elif method == "lda":
        return extract_with_lda(text_or_list, DEFAULT_STOPWORDS, top_n, return_counts=True)
    else:  # keybert
        return extract_with_keybert(text_or_list, top_n=top_n, return_counts=True)

# ✅ 뉴스 기사 목록 애스케 캐시 조회
async def get_news_articles_with_cache(
    keyword: str,
    start_date: str,
    end_date: str,
    unified_category=None,
    incident_category=None
):
    """📦 뉴스 기사 목록 캐시 조회"""
    async def fetch_from_mongo(**kwargs):
        return get_articles_by_conditions(**kwargs)

    return await get_or_cache(
        prefix="news_articles",
        fetch_func=fetch_from_mongo,
        ttl=settings.cache_expire_time,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        unified_category=unified_category or [],
        incident_category=incident_category or []
    )

# ✅ 키워드 분석 결과 캐시 조회
async def get_keyword_analysis_with_cache(
    keyword: str,
    method: str,
    start_date: str,
    end_date: str
):
    """📦 키워드 분석 결과 캐시 조회"""
    async def fetch_from_mongo(**kwargs):
        query = {
            "keyword": kwargs["keyword"],
            "method": kwargs["method"],
            "date_range.start": kwargs["start_date"],
            "date_range.end": kwargs["end_date"]
        }
        return db["keyword_analysis"].find_one(query, {"_id": 0})

    return await get_or_cache(
        prefix="keyword_analysis",
        fetch_func=fetch_from_mongo,
        ttl=settings.review_analysis_cache_expire_time,
        keyword=keyword,
        method=method,
        start_date=start_date,
        end_date=end_date
    )


async def crawl_and_extract_keywords_with_cache(req):
    redis_key = make_redis_key(
        prefix="keyword_extraction_result",
        keyword=req.keyword,
        start_date=req.start_date,
        end_date=req.end_date,
        method=req.method,
        unified_category=req.unified_category or [],
        incident_category=req.incident_category or [],
        top_n=req.top_n or 10,
        max_articles=req.max_articles,
        aggregate_mode="individual" if req.aggregate_from_individual else "summary"
    )

    # ✅ [1] 최신 뉴스 중 새 기사 확인 → Redis 무효화
    try:
        latest_articles = get_latest_articles(req.keyword, max_articles=5)
        latest_keys = [(a.get("title", ""), a.get("date", "")) for a in latest_articles if a.get("title") and a.get("date")]

        existing_map = find_existing_bulk(latest_keys, model="keyword_" + req.method)
        if len(existing_map) < len(latest_keys):
            print("🚨 새 뉴스 발견 → 키워드 Redis 캐시 무효화")
            await redis_client.delete(redis_key)
    except Exception as e:
        print(f"⚠️ 최신 뉴스 확인 실패 (무시하고 계속 진행): {e}")

    # ✅ [2] Redis HIT 시 바로 반환
    cached_result = await redis_client.get_json(redis_key)
    if cached_result:
        print(f"📦 [Redis] 키워드 추출 결과 캐시 HIT → {redis_key}")
        return cached_result

    # ✅ [3] 캐시 MISS → 추출 실행
    result = crawl_and_extract_keywords(req)  # 기존 동기 함수 그대로 사용 가능

    if result:
        await redis_client.set_json(
            redis_key,
            result,
            expire=settings.review_analysis_cache_expire_time
        )
        print(f"🧠 키워드 추출 결과 Redis 저장 완료 → {redis_key}")

    return result



