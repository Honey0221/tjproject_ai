from pydantic import BaseModel, Field
from typing import Optional


class ErrorResponse(BaseModel):
  """에러 응답 스키마"""
  error: str = Field(..., description="에러 메시지")
  detail: Optional[str] = Field(None, description="상세 정보")