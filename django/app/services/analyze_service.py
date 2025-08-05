import os
import joblib
import time
import torch
from crawling.bigKindsCrawling import search_bigkinds
from crawling.latestNewsCrawling import get_latest_articles
from app.utils.emotion_model_loader import (
    MODEL_DIR, ALLOWED_MODELS, embedding_model, hf_tokenizer, hf_model, id2label
)
from fastapi import HTTPException


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
    """
    통합분류, 사건사고분류, 날짜 범위를 기반으로
    BigKinds에서 뉴스 수집 후 감정 분석
    """
    from crawling.driver import undetected_driver

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
            max_articles=req.max_articles
        )
    except RuntimeError as e:
        driver.quit()
        raise HTTPException(status_code=204, detail=f"기사 수집 실패: {str(e)}")
    except Exception as e:
        driver.quit()
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

    driver.quit()

    if not articles:
        raise HTTPException(status_code=204, detail="검색 조건에 해당하는 뉴스가 없습니다.")

    return _analyze_articles(articles, req.model, req.keyword)


def emotion_batch(req):
    """
    감정 분석 없이 기사만 수집하는 API (데이터 저장 또는 후처리용)
    """
    from crawling.driver import undetected_driver

    start_date = req.start_date or "2025-01-01"
    end_date = req.end_date or time.strftime("%Y-%m-%d")

    driver = undetected_driver(headless=True)

    try:
        articles = search_bigkinds(
            driver=driver,
            keyword=req.keyword,
            unified_category=req.unified_category,
            incident_category=req.incident_category,
            start_date=start_date,
            end_date=end_date,
            date_method=req.date_method,
            period_label=req.period_label,
            max_articles=req.max_articles
        )
    except Exception as e:
        driver.quit()
        raise HTTPException(status_code=500, detail=f"기사 수집 중 오류 발생: {str(e)}")

    driver.quit()

    if not articles:
        raise HTTPException(status_code=204, detail="수집된 뉴스가 없습니다.")

    return {
        "count": len(articles),
        "data": articles
    }


def _analyze_articles(articles, model_key, keyword):
    """
    주어진 기사 목록(articles)에 대해 감정 분석을 수행하는 내부 함수

    - transformer: HuggingFace 기반 모델 사용
    - vote/stack: 전통 ML 모델 사용 (사전 임베딩 + joblib 로딩)
    """

    results = []

    if model_key not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 모델입니다: {model_key}")

    for article in articles:
        text = article.get("summary") or article.get("title", "")
        if not text.strip():
            continue

        try:
            # 🔍 HuggingFace 기반 transformer 모델
            if model_key == "transformer":
                inputs = hf_tokenizer(text, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    outputs = hf_model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=1)
                    conf, pred = torch.max(probs, dim=1)
                label = id2label[pred.item()]
                confidence = round(conf.item(), 4)

            # 🔍 전통 ML 앙상블 모델 (Voting/Stacking)
            else:
                model_path = os.path.join(MODEL_DIR, f"{model_key}.joblib")
                if not os.path.exists(model_path):
                    raise HTTPException(status_code=500, detail=f"모델 파일이 존재하지 않습니다: {model_path}")

                model = joblib.load(model_path)
                embedding = embedding_model.encode([text], show_progress_bar=False)
                prediction = model.predict(embedding)[0]
                confidence = model.predict_proba(embedding)[0].max()
                label = id2label[prediction]

            results.append({
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "press": article.get("press", ""),
                "date": article.get("date", ""),
                "link": article.get("link", ""),
                "label": label,
                "confidence": confidence
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"감정 분석 중 오류 발생: {str(e)}")

    if not results:
        raise HTTPException(status_code=204, detail="분석 가능한 텍스트가 없습니다.")

    return {
        "keyword": keyword,
        "count": len(results),
        "results": results
    }
