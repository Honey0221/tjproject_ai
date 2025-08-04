from pydantic import BaseModel, Field
from typing import List


class ReviewAnalysisRequest(BaseModel):
  """리뷰 분석 요청 스키마"""
  name: str = Field(..., description="기업명")


class KeywordItem(BaseModel):
  """키워드 항목 스키마"""
  keyword: str = Field(..., description="키워드")
  frequency: int = Field(..., description="빈도")


class ReviewSample(BaseModel):
  """리뷰 샘플 스키마"""
  review: str = Field(..., description="리뷰 내용")
  score: float = Field(..., description="점수")


class ReviewAnalysisData(BaseModel):
  """리뷰 분석 데이터 스키마"""
  avg_score: float = Field(..., description="평균 점수")
  keywords: List[KeywordItem] = Field(..., description="키워드 목록")
  sample_reviews: List[ReviewSample] = Field(..., description="샘플 리뷰")


class ReviewAnalysisResponse(BaseModel):
  """리뷰 분석 응답 스키마"""
  total_count: int = Field(..., description="총 리뷰 수")
  avg_score: float = Field(..., description="전체 평균 점수")
  pros: ReviewAnalysisData = Field(..., description="긍정 분석 결과")
  cons: ReviewAnalysisData = Field(..., description="부정 분석 결과")