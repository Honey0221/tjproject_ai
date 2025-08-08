from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class InquiryRequest(BaseModel):
  """문의하기 요청 스키마"""
  user_name: str = Field(..., description="사용자 이름")
  inquiry_title: str = Field(..., description="문의 제목")
  inquiry_type: str = Field(..., description="문의 유형")
  inquiry_content: str = Field(
    ..., min_length=1, max_length=2000, description="문의 내용")

class InquiryResponse(BaseModel):
  """문의하기 응답 스키마"""
  message: str = Field(..., description="응답 메시지")

class InquiryItem(BaseModel):
  """문의사항 항목 스키마"""
  id: int = Field(..., description="문의 ID")
  user_name: str = Field(..., description="사용자 이름")
  inquiry_title: str = Field(..., description="문의 제목")
  inquiry_type: str = Field(..., description="문의 유형")
  inquiry_content: str = Field(..., description="문의 내용")
  created_at: datetime = Field(..., description="생성 시간")

class InquiryListResponse(BaseModel):
  """문의사항 목록 응답 스키마"""
  inquiries: List[InquiryItem] = Field(..., description="문의사항 목록")