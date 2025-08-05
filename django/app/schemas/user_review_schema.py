from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReviewCreate(BaseModel):
  """리뷰 작성 요청"""
  companyId: str = Field(..., description="기업 ID")
  parentId: Optional[str] = Field(None, description="원글 ID (대댓글인 경우)")
  content: str = Field(..., min_length=1, max_length=1000, description="리뷰 내용")

class ReviewUpdate(BaseModel):
  """리뷰 수정 요청"""
  content: str = Field(..., min_length=1, max_length=1000, description="수정할 리뷰 내용")

class ReviewResponse(BaseModel):
  """리뷰 응답"""
  id: str = Field(..., description="리뷰 ID")
  userId: int = Field(..., description="작성자 ID")
  companyId: str = Field(..., description="기업 ID")
  parentId: Optional[str] = Field(None, description="원글 ID")
  content: str = Field(..., description="리뷰 내용")
  depth: int = Field(..., description="댓글 깊이")
  likeCount: int = Field(..., description="공감 수")
  createdAt: datetime = Field(..., description="작성 시간")
  updatedAt: datetime = Field(..., description="수정 시간")
  deletedAt: Optional[datetime] = Field(None, description="삭제 시간")
  replies: List['ReviewResponse'] = Field(default=[], description="대댓글 목록")

class ReviewListResponse(BaseModel):
  """리뷰 목록 응답"""
  total: int = Field(..., description="전체 리뷰 수")
  reviews: list[ReviewResponse] = Field(..., description="리뷰 목록")

class ReviewCreateResponse(BaseModel):
  """리뷰 작성 성공 응답"""
  message: str = Field(..., description="응답 메시지")
  reviewId: str = Field(..., description="생성된 리뷰 ID")

# Forward reference 해결
ReviewResponse.model_rebuild()