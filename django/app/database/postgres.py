from tortoise import Tortoise
from ..config import settings

class TortoiseManager:
  """Tortoise ORM 연결을 관리하는 싱글톤 클래스"""
  _instance = None
  _is_connected = False

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(TortoiseManager, cls).__new__(cls)
    return cls._instance

  async def connect(self):
    """Tortoise ORM 연결 초기화"""
    try:
      await Tortoise.init(config=settings.tortoise_orm_config)
      await Tortoise.generate_schemas()
      
      self._is_connected = True
    except Exception as e:
      self._is_connected = False
      if settings.require_external_services:
        raise e

  async def disconnect(self):
    """Tortoise ORM 연결 종료"""
    if self._is_connected:
      await Tortoise.close_connections()
      self._is_connected = False

  @property
  def is_connected(self):
    """연결 상태 반환"""
    return self._is_connected


# 전역 인스턴스
tortoise_manager = TortoiseManager()