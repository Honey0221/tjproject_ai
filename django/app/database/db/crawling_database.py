# app/database/db/crawling_database.py
from pymongo import MongoClient, ASCENDING
from datetime import datetime
import json

# ✅ MongoDB 연결 및 기본 컬렉션 참조
client = MongoClient("mongodb://localhost:27017")
db = client["news_analysis"]
collection = db["news_articles"]

def ensure_indexes():
    """
    ✅ (title, date, model) 기준 유니크 인덱스 생성
    - 동일 기사(title+date)가 같은 모델로 중복 저장되지 않도록 방지
    - 최초 1회만 실행되면 됨 (앱 시작 시)
    """
    collection.create_index(
        [("title", ASCENDING), ("date", ASCENDING), ("model", ASCENDING)],
        unique=True,
        name="uniq_title_date_model",
    )

def find_existing_article(title, date, model):
    """
    ✅ 단일 기사 존재 여부 확인용
    - 주어진 title, date, model로 MongoDB에서 기사 1건 조회
    """
    return collection.find_one({"title": title, "date": date, "model": model})

def find_existing_bulk(keys, model):
    """
    ✅ 여러 기사 존재 여부 일괄 확인용
    - keys: [(title, date), ...] 형식의 키 리스트
    - 반환: {(title, date): document} 딕셔너리
    - 중복 저장을 피하기 위해 사전 확인 시 사용
    """
    titles = list({t for t, _ in keys})
    dates  = list({d for _, d in keys})

    cursor = collection.find({
        "model": model,
        "title": {"$in": titles},
        "date":  {"$in": dates}
    })
    docs = list(cursor)
    return {(doc.get("title",""), doc.get("date","")): doc for doc in docs}

def upsert_article(article, label, confidence, keyword, model):
    """
    ✅ 기사 분석 결과 저장 (upsert)
    - 존재 시 업데이트, 없으면 삽입
    - 기준: (title, date, model)
    - 감정 분석 결과(label, confidence), 키워드 포함
    """

    summary = article.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        print(f"⚠️ 기사 요약이 비어 있어 저장 생략: {article.get('title')}")
        return  # ✅ 저장 안 하고 종료

    now = datetime.utcnow()
    article_record = {
        "title": article.get("title", ""),
        "summary": summary.strip(),  # ✅ 안전하게 strip()
        "press": article.get("press", ""),
        "writer": article.get("writer", ""),
        "date": article.get("date", ""),
        "link": article.get("link", ""),
        "keyword": keyword,
        "model": model,
        "label": label,
        "confidence": confidence,
        "analyzed_at": now,
        "updated_at": now,
    }

    result = collection.update_one(
        {"title": article["title"], "date": article["date"], "model": model},
        {"$set": article_record, "$setOnInsert": {"created_at": now}},
        upsert=True
    )

    if result.matched_count > 0:
        print(f"✅ [DB] 기존 기사 업데이트됨: {article['title']} ({model})")
    elif result.upserted_id:
        print(f"🆕 [DB] 새 기사 저장됨: {article['title']} ({model})")


def get_existing_keys():
    """
    ✅ 내부 디버깅용 함수
    - 기존 저장된 기사들의 (title, date, press, link) 세트 반환
    """
    cursor = collection.find({}, {"title": 1, "date": 1, "press": 1, "link": 1, "_id": 0})
    return set((doc["title"], doc["date"], doc.get("press", ""), doc.get("link", "")) for doc in cursor)


def get_articles_by_conditions(keyword, start_date, end_date, unified_category=None, incident_category=None):
    """
    ✅ 주어진 조건에 따라 DB에서 기존 저장된 기사들을 조회
    """
    query = {
        "title": {"$regex": keyword, "$options": "i"},
        "date": {"$gte": start_date, "$lte": end_date}
    }

    if unified_category:
        query["unified_category"] = {"$in": unified_category}
    if incident_category:
        query["incident_category"] = {"$in": incident_category}

    return list(collection.find(
        query,
        {
            "_id": 0,
            "title": 1,
            "summary": 1,
            "press": 1,
            "writer": 1,
            "date": 1,
            "link": 1,
            "keyword": 1,
            "model": 1
        }
    ).sort("_id", 1))


# ✅ 최근 키워드 기사 5개 조회용
def get_articles_by_keyword_recent(keyword: str, limit: int = 5):
    cursor = collection.find(
        {"keyword": keyword, "model": "latest"},
        {
            "_id": 0,
            "title": 1,
            "summary": 1,   # ✅ 추가
            "press": 1,
            "writer": 1,
            "date": 1,
            "link": 1,
            "keyword": 1
        }
    ).sort("date", -1).limit(limit)

    return list(cursor)

# ✅ 뉴스 키워드 추출 개별 및 전체 뉴스 통합
def save_overall_keywords(
    keyword: str,
    method: str,
    overall_keywords: list,
    individual_keywords: list,
    start_date: str,
    end_date: str,
    unified_category=None,
    incident_category=None
):
    now = datetime.utcnow()
    collection = db["keyword_analysis"]

    # ✅ 전체 키워드 비율 계산
    if overall_keywords and isinstance(overall_keywords[0], (tuple, list)):
        total_score = sum(score for _, score in overall_keywords if isinstance(score, (int, float)))
        formatted_overall = [
            {
                "keyword": kw,
                "score": round(score, 4),
                "ratio": round(score / total_score * 100, 1) if total_score > 0 else 0
            }
            for kw, score in overall_keywords
        ]
    else:
        formatted_overall = overall_keywords

    # ✅ 개별 기사별 키워드 구조 정비
    formatted_individual = []
    for idx, doc in enumerate(individual_keywords):
        title = doc.get("title", f"기사 {idx + 1}")
        raw_keywords = doc.get("keywords", [])
        count = doc.get("count", len(raw_keywords))
        ratio = round(doc.get("ratio", 0) * 100, 1)  # 0.23 → 23.0%

        if raw_keywords and isinstance(raw_keywords[0], (tuple, list)):
            total = sum(score for _, score in raw_keywords if isinstance(score, (int, float)))
            formatted_keywords = [
                {
                    "keyword": kw,
                    "score": round(score, 4),
                    "ratio": round(score / total * 100, 1) if total > 0 else 0
                }
                for kw, score in raw_keywords
            ]
        elif raw_keywords and isinstance(raw_keywords[0], dict):
            # 이미 정제된 형태일 경우 그대로 사용
            formatted_keywords = raw_keywords
        else:
            formatted_keywords = []

        formatted_individual.append({
            "title": title,
            "count": count,
            "ratio": ratio,
            "keywords": formatted_keywords
        })

    # ✅ MongoDB 저장
    doc = {
        "keyword": keyword,
        "method": method,
        "overall_keywords": formatted_overall,
        "individual_keywords": formatted_individual,
        "date_range": {
            "start": start_date,
            "end": end_date
        },
        "unified_category": unified_category,
        "incident_category": incident_category,
        "analyzed_at": now
    }

    collection.insert_one(doc)
    print(f"✅ [DB] 키워드 분석 결과 저장 완료: {keyword} ({method})")



# 모델 상관없이 summary만 찾아주는 함수
def find_summary_any_model(title, date):
    doc = collection.find_one(
        {
            "title": title,
            "date": date,
            "summary": {"$exists": True, "$ne": ""}
        },
        {"summary": 1}
    )
    return doc.get("summary") if doc else None


