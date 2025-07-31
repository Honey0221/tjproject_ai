from tortoise.models import Model
from tortoise import fields, Tortoise
from ..config import settings
from datetime import datetime

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

class Inquiry(Model):
  """문의사항 모델"""
  id = fields.IntField(pk=True)
  inquiry_type = fields.CharField(max_length=100, description="문의 유형")
  inquiry_content = fields.TextField(description="문의 내용")
  created_at = fields.DatetimeField(auto_now_add=True, description="생성 시간")

  class Meta:
    table = "inquiries"
    ordering = ["-created_at"]

  def __str__(self):
    return f"Inquiry({self.id}): {self.inquiry_type}"

  @classmethod
  async def create_inquiry(cls, inquiry_type, inquiry_content):
    """문의사항 생성"""
    try:
      return await cls.create(
        inquiry_type=inquiry_type,
        inquiry_content=inquiry_content,
        created_at=datetime.now()
      )
    except Exception as e:
      print(f"문의사항 생성 오류: {str(e)}")
      raise e

  @classmethod
  async def get_by_type(cls, inquiry_type):
    """유형별 문의사항 조회"""
    try:
      return await cls.filter(inquiry_type=inquiry_type).order_by('-created_at')
    except Exception as e:
      print(f"유형별 문의사항 조회 오류: {str(e)}")
      raise e

  @classmethod
  async def get_recent(cls, limit = 20):
    """최근 문의사항 조회"""
    try:
      return await cls.all().order_by('-created_at').limit(limit)
    except Exception as e:
      print(f"최근 문의사항 조회 오류: {str(e)}")
      raise e

  @classmethod
  async def count_by_type(cls, inquiry_type):
    """유형별 문의사항 개수"""
    try:
      return await cls.filter(inquiry_type=inquiry_type).count()
    except Exception as e:
      print(f"유형별 문의사항 개수 조회 오류: {str(e)}")
      raise e

# 전역 인스턴스
tortoise_manager = TortoiseManager()