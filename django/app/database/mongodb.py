from motor.motor_asyncio import AsyncIOMotorClient
from ..config import settings

class MongoDBManager:
  """비동기 MongoDB 연결을 관리하는 싱글톤 클래스"""
  _instance = None
  _client = None
  _db = None
  _is_connected = False

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(MongoDBManager, cls).__new__(cls)
    return cls._instance

  async def connect(self):
    """MongoDB 연결 초기화"""
    try:
      self._client = AsyncIOMotorClient(settings.mongodb_url)
      self._db = self._client[settings.mongodb_db]
      
      # 연결 테스트
      await self._client.admin.command('ismaster')
      self._is_connected = True
    except Exception as e:
      self._is_connected = False
      if settings.require_external_services:
        raise e
      else:
        self._client = None
        self._db = None

  async def disconnect(self):
    """MongoDB 연결 종료"""
    if self._client:
      self._client.close()
      self._client = None
      self._db = None
      self._is_connected = False

  @property
  def db(self):
    """데이터베이스 인스턴스 반환"""
    if not self._is_connected and settings.require_external_services:
      raise ConnectionError("MongoDB 연결이 초기화되지 않았습니다.")
    return self._db

  @property
  def client(self):
    """클라이언트 인스턴스 반환"""
    if not self._is_connected and settings.require_external_services:
      raise ConnectionError("MongoDB 클라이언트가 초기화되지 않았습니다.")
    return self._client

  @property
  def is_connected(self):
    """연결 상태 반환"""
    return self._is_connected

# 전역 인스턴스
mongodb_manager = MongoDBManager() 