import os
import json
from crawling.latestNewsCrawling import get_latest_articles
from fastapi import HTTPException
from keybert import KeyBERT
from driver import undetected_driver
from crawling.bigKindsCrawling import search_bigkinds
from app.utils.keyword_extractors import (
    extract_with_keybert, extract_with_tfidf,
    extract_with_krwordrank, extract_with_lda, extract_with_okt
)
from app.utils.stopwords import DEFAULT_STOPWORDS

# ✅ 한국어 SBERT 기반 KeyBERT 모델 초기화
kw_model = KeyBERT(model="jhgan/ko-sbert-nli")


def crawl_latest_articles(keyword: str, headless: bool = True):
    """
    ✅ 키워드 기반 최신 뉴스 5건 실시간 수집 (BigKinds 사용)
    """
    articles = get_latest_articles(keyword, max_articles=5, headless=headless)
    if not articles:
        raise HTTPException(status_code=404, detail="해당 키워드에 대한 최신 기사가 없습니다.")
    return articles


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


def extract_keywords_from_articles(req):
    """
    ✅ 날짜/카테고리 필터 기반 뉴스 수집 후 키워드 추출
    - method: tfidf, krwordrank, lda, okt, keybert 중 선택
    """
    # ✅ 추출 방식 유효성 검사
    ALLOWED_METHODS = {"tfidf", "krwordrank", "lda", "okt", "keybert"}
    if req.method not in ALLOWED_METHODS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 추출 방식입니다: {req.method}")

    driver = undetected_driver(headless=req.headless)
    try:
        articles = search_bigkinds(
            driver=driver,
            keyword=req.keyword,
            unified_category=req.unified_category,
            incident_category=req.incident_category,
            start_date=req.start_date,
            end_date=req.end_date,
            date_method=req.date_method,
            period_label=req.period_label,
            max_articles=req.max_articles,
        )

        if not articles:
            raise HTTPException(
                status_code=404,
                detail="검색 조건에 해당하는 뉴스가 없습니다. 키워드를 바꾸거나 날짜/카테고리를 넓혀 다시 시도해주세요."
            )

        individual_results = []
        all_texts = []

        for article in articles:
            summary = article.get("summary", "")
            title = article.get("title", "")
            if summary.strip():
                all_texts.append(summary)

                # 개별 기사 키워드 추출
                if req.method == "tfidf":
                    keywords = extract_with_tfidf([summary], DEFAULT_STOPWORDS)
                elif req.method == "krwordrank":
                    keywords = extract_with_krwordrank(summary, DEFAULT_STOPWORDS)
                elif req.method == "okt":
                    keywords = extract_with_okt([summary], DEFAULT_STOPWORDS)
                elif req.method == "lda":
                    keywords = []  # 개별 기사에서는 생략
                else:  # default = keybert
                    keywords = extract_with_keybert(summary, DEFAULT_STOPWORDS)

                individual_results.append({"title": title, "keywords": keywords})

        # ✅ 전체 기사 요약 기준 키워드 (종합)
        if not all_texts:
            raise HTTPException(
                status_code=404,
                detail="요약이 포함된 뉴스가 없어 키워드를 추출할 수 없습니다."
            )

        if req.method == "lda":
            overall_keywords = extract_with_lda(all_texts, DEFAULT_STOPWORDS)
        elif req.method == "okt":
            overall_keywords = extract_with_okt(all_texts, DEFAULT_STOPWORDS)
        elif req.method == "tfidf":
            overall_keywords = extract_with_tfidf(all_texts, DEFAULT_STOPWORDS)
        elif req.method == "krwordrank":
            combined_text = " ".join(all_texts)
            overall_keywords = extract_with_krwordrank(combined_text, DEFAULT_STOPWORDS)
        else:
            combined_text = " ".join(all_texts)
            overall_keywords = extract_with_keybert(combined_text, DEFAULT_STOPWORDS, top_n=10)

        return {
            "count": len(articles),
            "individual_keywords": individual_results,
            "overall_keywords": overall_keywords
        }

    finally:
        driver.quit()  # ✅ 예외 발생 여부와 관계없이 무조건 종료
