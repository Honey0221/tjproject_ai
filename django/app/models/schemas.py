from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class Company(BaseModel):
  """기본 정보 스키마"""
  id: Optional[str] = Field(None, description="기업 ID")
  name: str = Field(..., description="기업명")
  산업_분야: Optional[str] = Field(None, description="산업 분야")
  crawled_at: Optional[Union[str, datetime]] = Field(None, description="크롤링 시간")

  # 재무 정보
  매출액: Optional[str] = Field(None, description="매출액")
  영업이익: Optional[str] = Field(None, description="영업이익") 
  순이익: Optional[str] = Field(None, description="순이익")
  
  # 기타 필드들은 동적 처리
  extra_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)

  @field_validator('crawled_at', mode='before')
  @classmethod
  def parse_crawled_at(cls, v):
    """crawled_at 필드를 ISO 형식 문자열로 변환"""
    if isinstance(v, datetime):
      return v.isoformat()
    return str(v)

  def model_dump(self, **kwargs):
    """딕셔너리 변환 시 extra_fields를 병합"""
    d = super().model_dump(**kwargs)
    if self.extra_fields:
      d.update(self.extra_fields)
    d.pop('extra_fields')  # extra_fields 키는 제거
    return d

  @classmethod
  def from_mongo_doc(cls, doc: Dict[str, Any]) -> 'Company':
    """MongoDB 문서에서 Pydantic 모델 생성"""
    
    # _id 필드를 id로 변환
    if '_id' in doc:
      doc['id'] = str(doc['_id'])
      del doc['_id']
    
    # 필드명의 공백을 언더스코어로 변환
    normalized_doc = {}
    extra_fields = {}
    
    for key, value in doc.items():
      normalized_key = key.replace(' ', '_').replace('-', '_')
      
      # 정의된 필드인지 확인
      if normalized_key in cls.model_fields:
        normalized_doc[normalized_key] = value
      else:
        # 추가 필드로 저장
        extra_fields[normalized_key] = value
    
    if extra_fields:
      normalized_doc['extra_fields'] = extra_fields
    
    return cls(**normalized_doc)

class CompanySearchRequest(BaseModel):
  """기업 검색 요청 스키마"""
  name: Optional[str] = Field(None, description="기업명")
  category: Optional[str] = Field(None, description="카테고리")

class CompanySearchResponse(BaseModel):
  """기업 검색 응답 스키마"""
  search_type: str = Field(..., description="검색 유형")
  search_keyword: str = Field(..., description="검색 키워드")
  total_count: int = Field(..., description="총 검색 결과 수")
  companies: List[Company] = Field(..., description="기업 목록")

class RankingItem(BaseModel):
  """랭킹 항목 스키마"""
  name: str = Field(..., description="기업명")
  amount: float = Field(..., description="금액")
  year: int = Field(..., description="연도")

class CompanyRankingResponse(BaseModel):
  """기업 랭킹 응답 스키마"""
  매출액: List[RankingItem] = Field(..., description="매출액 랭킹")
  영업이익: List[RankingItem] = Field(..., description="영업이익 랭킹")
  순이익: List[RankingItem] = Field(..., description="순이익 랭킹")

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

class CompanyItem(BaseModel):
  """기업 아이템 모델"""
  name: str = Field(..., description="기업명")
  summary: str = Field(..., description="기업 요약(최대 30자)")

class CompanySearchResult(BaseModel):
  """기업 검색 결과 (챗봇용)"""
  search_keyword: str = Field(..., description="검색 키워드")
  companies: List[CompanyItem] = Field(..., description="기업 목록 (최대 3개)")

class NewsItem(BaseModel):
  """뉴스 아이템 모델"""
  title: str = Field(..., description="뉴스 제목")
  summary: str = Field(..., description="뉴스 요약")
  url: str = Field(..., description="뉴스 원문 URL")

class CompanyNewsResult(BaseModel):
  """기업 뉴스 검색 결과 (챗봇용)"""
  company_name: str = Field(..., description="기업명")
  news_list: List[NewsItem] = Field(..., description="뉴스 목록 (최대 3개)")
  
class ErrorResponse(BaseModel):
  """에러 응답 스키마"""
  error: str = Field(..., description="에러 메시지")
  detail: Optional[str] = Field(None, description="상세 정보") 