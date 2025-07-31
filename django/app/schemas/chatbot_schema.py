from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InquiryRequest(BaseModel):
  """문의하기 요청 스키마"""
  inquiry_type: str = Field(..., description="문의 유형 (예: 일반문의, 기술지원, 제품문의 등)")
  inquiry_content: str = Field(..., min_length=1, max_length=2000, description="문의 내용")

class InquiryResponse(BaseModel):
  """문의하기 응답 스키마"""
  message: str = Field(..., description="응답 메시지")