import os
import joblib
import time
import torch
from crawling.bigKinds_crawling_speed import search_bigkinds
from datetime import datetime, timedelta
from crawling.latest_news_crawling import get_latest_articles
from app.utils.emotion_model_loader import (
    MODEL_DIR, ALLOWED_MODELS, embedding_model, hf_tokenizer, hf_model, id2label
)

from app.database.db.crawling_database import get_articles_by_conditions


from fastapi import HTTPException


from app.utils.news_keywords_cache_utils import get_or_cache
from app.database.db.crawling_database import get_articles_by_conditions
from app.config import settings



#MongoDB 관련
from datetime import datetime
from ..database.db.crawling_database import (
    find_existing_article,
    find_existing_bulk,  # ✅ 이거 꼭 추가!
    upsert_article,
    ensure_indexes,
)
from app.utils.news_keywords_cache_utils import get_or_cache, make_redis_key
from app.database.redis_client import redis_client


MAX_ANALYSIS_AGE = timedelta(days=7)  # 갱신 기준 (7일)

def analyze_news(req):
    """
    키워드 기반으로 최신 뉴스 기사들을 수집한 후,
    선택된 모델(vote, stack, transformer)로 감정 분석 수행
    """
    articles = get_latest_articles(req.keyword, req.max_articles, headless=req.headless)
    if not articles:
        raise HTTPException(status_code=204, detail="해당 키워드로 수집된 뉴스가 없습니다.")
    return _analyze_articles(articles, req.model, req.keyword)


def analyze_news_filtered(req):
    # 1. 기존 조건에 해당하는 기사 조회
    existing_articles = get_articles_by_conditions(
        keyword=req.keyword,
        start_date=req.start_date,
        end_date=req.end_date,
        unified_category=req.unified_category,
        incident_category=req.incident_category
    )

    # 2. 있으면 크롤링 생략
    if existing_articles:
        return existing_articles  # 또는 이걸로 키워드/감정 분석 수행
    config = {
        "keyword": req.keyword,
        "unified_category": req.unified_category,
        "incident_category": req.incident_category,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "date_method": req.date_method,
        "period_label": req.period_label,
        "max_articles": req.max_articles,
        "headless": req.headless
    }

    try:
        articles = search_bigkinds(
            keyword=config["keyword"],
            unified_category=config.get("unified_category"),
            incident_category=config.get("incident_category"),
            start_date=config.get("start_date"),
            end_date=config.get("end_date"),
            date_method=config.get("date_method", "preset"),
            period_label=config.get("period_label"),
            max_articles=config.get("max_articles")
        )
    except RuntimeError as e:
        raise HTTPException(status_code=204, detail=f"기사 수집 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

    if not articles:
        raise HTTPException(status_code=204, detail="검색 조건에 해당하는 뉴스가 없습니다.")

    return _analyze_articles(articles, req.model, req.keyword)


async def analyze_news_filtered_with_cache(req):
    """
    ✅ Redis 캐시 기반 필터 뉴스 감정 분석
    - 기사 목록 조회 + 감정 분석 결과 전체를 Redis에 저장
    """

    # Redis 키: 분석 결과 전체 기준
    redis_key = make_redis_key(
        prefix="emotion_analysis_result",
        keyword=req.keyword,
        start_date=req.start_date,
        end_date=req.end_date,
        unified_category=req.unified_category or [],
        incident_category=req.incident_category or [],
        model=req.model,
        max_articles=req.max_articles
    )

    # 1. Redis에서 감정 분석 결과 전체 조회
    cached_result = await redis_client.get_json(redis_key)
    if cached_result:
        print(f"📦 [Redis] 감정 분석 결과 캐시 HIT → {redis_key}")
        return cached_result

    # 2. MongoDB에서 기존 기사 조회
    existing_articles = get_articles_by_conditions(
        keyword=req.keyword,
        start_date=req.start_date,
        end_date=req.end_date,
        unified_category=req.unified_category,
        incident_category=req.incident_category
    )

    # 3. 있으면 분석 진행
    if existing_articles:
        print(f"🔄 [MongoDB] 기존 기사 {len(existing_articles)}건 분석 수행")
        result = _analyze_articles(existing_articles, req.model, req.keyword)
    else:
        # 4. 없으면 크롤링
        print(f"🌐 [크롤링 시작] 조건에 맞는 기사 없음 → 크롤링 진행")
        crawled_articles = search_bigkinds(
            keyword=req.keyword,
            unified_category=req.unified_category,
            incident_category=req.incident_category,
            start_date=req.start_date,
            end_date=req.end_date,
            date_method=req.date_method,
            period_label=req.period_label,
            max_articles=req.max_articles
        )

        if not crawled_articles:
            raise HTTPException(status_code=204, detail="수집된 뉴스가 없습니다.")

        result = _analyze_articles(crawled_articles, req.model, req.keyword)

    # 5. 분석 결과 Redis에 캐시
    if result:
        await redis_client.set_json(
            redis_key,
            result,
            expire=settings.review_analysis_cache_expire_time
        )
        print(f"🧠 Redis에 분석 결과 저장 완료 → {redis_key}")

    return result



def emotion_batch(req):
    start_date = req.start_date or "2025-01-01"
    end_date = req.end_date or time.strftime("%Y-%m-%d")

    config = {
        "keyword": req.keyword,
        "unified_category": req.unified_category,
        "incident_category": req.incident_category,
        "start_date": start_date,
        "end_date": end_date,
        "date_method": req.date_method,
        "period_label": req.period_label,
        "max_articles": req.max_articles,
        "headless": True
    }

    try:
        # ✅ config 딕셔너리를 언패킹해서 전달
        articles = search_bigkinds(
            keyword=config["keyword"],
            unified_category=config.get("unified_category"),
            incident_category=config.get("incident_category"),
            start_date=config.get("start_date"),
            end_date=config.get("end_date"),
            date_method=config.get("date_method", "preset"),
            period_label=config.get("period_label"),
            max_articles=config.get("max_articles")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기사 수집 중 오류 발생: {str(e)}")

    if not articles:
        raise HTTPException(status_code=204, detail="수집된 뉴스가 없습니다.")

    return {
        "count": len(articles),
        "data": articles
    }



def _analyze_articles(articles, model_key, keyword):
    start_time = datetime.now()  # ✅ 시작 시간 기록

    if model_key not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 모델입니다: {model_key}")

    # ✅ 앱 기동 시 1회만 호출되도록 옮겨도 됨
    try:
        ensure_indexes()
    except Exception:
        pass

    # 1) 전처리: 텍스트 없는 기사 제외 + 키 생성
    cleaned = []
    keys = []
    for a in articles:
        title = a.get("title", "")
        date  = a.get("date", "")
        text  = (a.get("summary") or title or "").strip()
        if not text:
            continue
        cleaned.append(a)
        keys.append((title, date))

    if not cleaned:
        raise HTTPException(status_code=204, detail="분석 가능한 텍스트가 없습니다.")




    # 2) ✅ 기존 문서 한 번에 조회 (DB 왕복 1회)
    existing_map = find_existing_bulk(keys, model_key)

    results = []
    reuse_count = 0
    new_count = 0
    now = datetime.utcnow()

    # 3) 원래 기사 순서를 유지하면서 “재사용/재분석/신규분석” 분기
    for article in cleaned:
        title = article.get("title", "")
        date  = article.get("date", "")
        text  = (article.get("summary") or title).strip()

        existing = existing_map.get((title, date))
        use_cached = False
        if existing:
            print(f"✅ DB 재사용: {title} ({existing['label']})")
            analyzed_at = existing.get("analyzed_at")
            if isinstance(analyzed_at, datetime) and (now - analyzed_at) < MAX_ANALYSIS_AGE:
                # ✅ 7일 이내 → 캐시 재사용, 모델 추론 X
                results.append({
                    "title": title,
                    "summary": article.get("summary", "") or article.get("summary"),
                    "press": article.get("press", ""),
                    "date": date,
                    "link": article.get("link", ""),
                    "label": existing["label"],
                    "confidence": existing["confidence"],
                })
                reuse_count += 1
                use_cached = True
            else:
                print(f"🔁 DB 저장됨 (7일 경과) → 재분석: {title}")
        else:
            print(f"🆕 신규 기사 분석: {title}")

        if use_cached:
            continue

        # 4) ✅ 새 기사 or 오래된 기사 → 모델 추론 수행
        try:
            if model_key == "transformer":
                inputs = hf_tokenizer(text, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    outputs = hf_model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=1)
                    conf, pred = torch.max(probs, dim=1)
                label = id2label[pred.item()]
                confidence = round(conf.item(), 4)
            else:
                model_path = os.path.join(MODEL_DIR, f"{model_key}.joblib")
                if not os.path.exists(model_path):
                    raise HTTPException(status_code=500, detail=f"모델 파일이 존재하지 않습니다: {model_path}")
                model = joblib.load(model_path)
                embedding = embedding_model.encode([text], show_progress_bar=False)
                prediction = model.predict(embedding)[0]
                confidence = float(model.predict_proba(embedding)[0].max())
                label = id2label[prediction]

            # 5) ✅ DB 저장/갱신 (upsert)
            upsert_article(article, label, confidence, keyword, model_key)
            results.append({
                "title": title,
                "summary": article.get("summary", ""),
                "press": article.get("press", ""),
                "date": date,
                "link": article.get("link", ""),
                "label": label,
                "confidence": confidence,
            })
            new_count += 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"감정 분석 중 오류 발생: {str(e)}")

    if not results:
        raise HTTPException(status_code=204, detail="분석 가능한 텍스트가 없습니다.")

    end_time = datetime.now()  # ✅ 끝나는 시간 기록
    elapsed = (end_time - start_time).total_seconds()

    print(f"⏱ 감정 분석 총 소요 시간: {elapsed:.2f}초")  # ✅ 백엔드 콘솔 출력용

    # (선택) 프런트에서 보기 좋게 집계 정보도 내려주기
    return {
        "keyword": keyword,
        "count": len(results),
        "reuse_count": reuse_count,
        "new_or_refreshed_count": new_count,
        "elapsed_seconds": round(elapsed, 2),
        "results": results,
    }