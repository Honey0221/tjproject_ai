import redis.asyncio as redis
import json
from ..config import settings

class RedisClient:
  """비동기 Redis 클라이언트를 관리하는 싱글톤 클래스"""
  _instance = None
  _redis = None
  _is_connected = False

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(RedisClient, cls).__new__(cls)
    return cls._instance

  async def connect(self):
    """Redis 연결 초기화"""
    try:
      self._redis = redis.from_url(
        settings.redis_url,
        decode_responses=True,
        encoding="utf-8"
      )
      
      # 연결 테스트
      await self._redis.ping()
      self._is_connected = True
      print(f"Redis 연결 성공: {settings.redis_host}:{settings.redis_port}")
    except Exception as e:
      self._is_connected = False
      if settings.require_external_services:
        print(f"Redis 연결 실패: {str(e)}")
        raise e
      else:
        print(f"⚠️ Redis 연결 실패 (개발 모드로 계속 실행): {str(e)}")
        self._redis = None

  async def disconnect(self):
    """Redis 연결 종료"""
    if self._redis:
      await self._redis.close()
      self._redis = None
      self._is_connected = False

  @property
  def redis(self):
    """Redis 인스턴스 반환"""
    if not self._is_connected and settings.require_external_services:
      raise ConnectionError("Redis 연결이 초기화되지 않았습니다.")
    return self._redis

  @property
  def is_connected(self):
    """연결 상태 반환"""
    return self._is_connected

  async def get(self, key):
    """키로 값 조회"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return None
      
    try:
      return await self.redis.get(key)
    except Exception as e:
      print(f"Redis GET 오류 ({key}): {str(e)}")
      return None

  async def set(self, key, value, expire=None):
    """키-값 저장"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return True
      
    try:
      if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
      
      if expire:
        return await self.redis.setex(key, expire, value)
      else:
        return await self.redis.set(key, value)
    except Exception as e:
      print(f"Redis SET 오류 ({key}): {str(e)}")
      return False

  async def setex(self, key, expire_seconds, value):
    """키-값을 만료 시간과 함께 저장 (Redis setex와 동일)"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return True
      
    try:
      if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
      
      return await self.redis.setex(key, expire_seconds, value)
    except Exception as e:
      print(f"Redis SETEX 오류 ({key}): {str(e)}")
      return False

  async def delete(self, *keys):
    """키 삭제"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return 0
      
    try:
      return await self.redis.delete(*keys)
    except Exception as e:
      print(f"Redis DELETE 오류: {str(e)}")
      return 0

  async def keys(self, pattern):
    """패턴으로 키 검색"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return []
      
    try:
      return await self.redis.keys(pattern)
    except Exception as e:
      print(f"Redis KEYS 오류 ({pattern}): {str(e)}")
      return []

  async def flushdb(self):
    """현재 DB의 모든 키 삭제"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return True
      
    try:
      return await self.redis.flushdb()
    except Exception as e:
      print(f"Redis FLUSHDB 오류: {str(e)}")
      return False

  async def get_json(self, key):
    """JSON 형태로 저장된 값 조회"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return None
      
    try:
      value = await self.get(key)
      if value:
        return json.loads(value)
      return None
    except json.JSONDecodeError as e:
      print(f"JSON 디코딩 오류 ({key}): {str(e)}")
      return None
    except Exception as e:
      print(f"Redis GET_JSON 오류 ({key}): {str(e)}")
      return None

  async def set_json(self, key, value, expire=None):
    """JSON 형태로 값 저장"""
    if not self.is_connected:
      print(f"Redis 연결이 초기화되지 않았습니다.")
      return True
      
    try:
      json_value = json.dumps(value, ensure_ascii=False)
      return await self.set(key, json_value, expire)
    except Exception as e:
      print(f"Redis SET_JSON 오류 ({key}): {str(e)}")
      return False

# 전역 인스턴스
redis_client = RedisClient() 