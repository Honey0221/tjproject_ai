from tortoise.models import Model
from tortoise import fields
from datetime import datetime

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