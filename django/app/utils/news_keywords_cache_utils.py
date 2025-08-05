# app/utils/news_keywords_cache_utils.py
from hashlib import md5
from app.database.redis_client import redis_client
from datetime import datetime
import json

def make_redis_key(prefix: str, **kwargs) -> str:
    """Redis 키 생성 (prefix + 쿼리 파라미터 해시)"""
    raw = "|".join(f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in sorted(kwargs.items()))
    return f"{prefix}:{md5(raw.encode()).hexdigest()}"


async def get_or_cache(prefix: str, fetch_func, ttl: int, **params):
    """
    ✅ Redis 캐시 조회 → 없으면 fetch_func 호출 후 캐싱
    - prefix: 캐시 키 앞부분
    - fetch_func: MongoDB 조회 함수
    - ttl: 캐시 유지 시간 (초)
    - params: 키 구성 및 Mongo 함수 인자로 사용됨
    """
    redis_key = make_redis_key(prefix, **params)

    # 1️⃣ 캐시 조회
    cached = await redis_client.get_json(redis_key)
    if cached:
        print(f"📦 [Redis] 캐시 HIT → {prefix}")
        return cached

    # 2️⃣ 캐시 없으면 MongoDB 조회
    print(f"🔍 [MongoDB] DB 조회 실행 → {prefix}")
    result = await fetch_func(**params)

    # 3️⃣ 직렬화 함수
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [serialize(i) for i in obj]
        return obj

    # 4️⃣ 빈 결과는 Redis에 저장하지 않음
    if result:
        try:
            serialized_result = serialize(result)
            await redis_client.set_json(redis_key, serialized_result, expire=ttl)
            print(f"🗓 Redis 저장 결과: {json.dumps(serialized_result, ensure_ascii=False)}")
        except Exception as e:
            print(f"⚠️ Redis 저장 오류 ({redis_key}): {e}")
    else:
        print(f"⚠️ 결과가 비어 있어 Redis에 저장하지 않음: {redis_key}")

    return result