import asyncio
import hashlib
import json
from typing import Any, Optional, Dict, List
import pandas as pd
from ..models.company import company_review_model
from ..database.redis_client import redis_client
from ..config import settings
from machine_model.company_review.review_dataset import ReviewDataset
from machine_model.company_review.review_analyzer import ReviewSentimentAnalyzer

class ReviewAnalysisService:
  """비동기 리뷰 분석 서비스"""
  def __init__(self) -> None:
    self.review_dataset = ReviewDataset()
    self.review_analyzer = ReviewSentimentAnalyzer()
    self._review_crawler = None
  
  def _get_cache_key(self, company_name: str) -> str:
    """리뷰 분석 캐시 키 생성"""
    # 기업명을 해시화하여 안전한 키 생성
    company_hash = hashlib.md5(company_name.encode()).hexdigest()
    return f"review_analysis:{company_hash}"
  
  def _serialize_for_cache(self, data: Any) -> Any:
    """캐시 저장을 위한 데이터 직렬화"""
    if isinstance(data, pd.DataFrame):
      # DataFrame을 딕셔너리로 변환 (records 형태)
      return {
        '_type': 'dataframe',
        'data': data.to_dict('records'),
        'columns': data.columns.tolist(),
        'shape': data.shape
      }
    elif isinstance(data, dict):
      # 딕셔너리의 각 값에 대해 재귀적으로 직렬화
      return {key: self._serialize_for_cache(value) for key, value in data.items()}
    elif isinstance(data, list):
      # 리스트의 각 항목에 대해 재귀적으로 직렬화
      return [self._serialize_for_cache(item) for item in data]
    elif isinstance(data, tuple):
      # 튜플을 리스트로 변환
      return [self._serialize_for_cache(item) for item in data]
    else:
      # 기본 타입은 그대로 반환
      return data
  
  def _deserialize_from_cache(self, data: Any) -> Any:
    """캐시에서 읽은 데이터 역직렬화"""
    if isinstance(data, dict) and data.get('_type') == 'dataframe':
      # DataFrame 복원
      return pd.DataFrame(data['data'], columns=data['columns'])
    elif isinstance(data, dict):
      # 딕셔너리의 각 값에 대해 재귀적으로 역직렬화
      return {key: self._deserialize_from_cache(value) for key, value in data.items()}
    elif isinstance(data, list):
      # 리스트의 각 항목에 대해 재귀적으로 역직렬화
      return [self._deserialize_from_cache(item) for item in data]
    else:
      # 기본 타입은 그대로 반환
      return data
  
  async def _get_from_cache(self, key: str) -> Any:
    """Redis 캐시에서 값 조회"""
    try:
      if redis_client.is_connected and redis_client._redis is not None:
        value = await redis_client.get(key)
        if value is not None:
          # JSON 파싱 시도
          try:
            json_data = json.loads(value)
            # 역직렬화 수행
            return self._deserialize_from_cache(json_data)
          except json.JSONDecodeError:
            return value
      return None
      
    except Exception as e:
      print(f"리뷰 분석 캐시 조회 오류: {str(e)}")
      return None
  
  async def _set_to_cache(self, key: str, value: Any, expire_seconds: int) -> bool:
    """Redis 캐시에 값 저장"""
    try:
      if redis_client.is_connected and redis_client._redis is not None:
        # 직렬화 수행
        serialized_value = self._serialize_for_cache(value)
        
        # JSON으로 변환
        redis_value = json.dumps(serialized_value, ensure_ascii=False)
        
        success = await redis_client.setex(key, expire_seconds, redis_value)
        if success:
          print(f"💾 Redis 리뷰 분석 캐시 저장 성공: {key}")
        return success
      return False
      
    except Exception as e:
      print(f"Redis 리뷰 분석 캐시 저장 오류: {str(e)}")
      return False

  async def analysis_review(self, name: str) -> Dict[str, Any]:
    """리뷰 분석 실행 (캐시 지원)"""
    
    # 1. 캐시에서 먼저 확인
    cache_key = self._get_cache_key(name)
    cached_result = await self._get_from_cache(cache_key)
    if cached_result:
      print(f"📦 캐시에서 리뷰 분석 결과 반환: {name}")
      return cached_result
    
    print(f"🔍 리뷰 분석 새로 실행: {name}")
    
    try:
      # 2. 실제 분석 수행
      analysis_result = await self._perform_analysis(name)
      
      # 3. 결과를 캐시에 저장
      cache_expire_time = settings.review_analysis_cache_expire_time
      await self._set_to_cache(cache_key, analysis_result, cache_expire_time)
      
      return analysis_result
      
    except Exception as e:
      print(f"리뷰 분석 중 오류 발생: {str(e)}")
      # 기본 응답 반환
      return self._get_default_response()

  async def get_reviews(self, name: str) -> List[Dict]:
    """기업 이름으로 리뷰 데이터 조회"""
    try:
      reviews = await company_review_model.get_reviews_by_company(name)
      
      # DB에 있으면 직렬화 후 반환
      if reviews:
        cleaned_reviews = []
        for review in reviews:
          clean_review = {}
          for key, value in review.items():
            if key == '_id':
              continue  # ObjectId 제외
            elif key == 'crawled_at':
              clean_review[key] = str(value)
            else:
              clean_review[key] = value
          cleaned_reviews.append(clean_review)
        return cleaned_reviews
      # DB에 없으면 크롤링 후 재귀적으로 다시 조회
      else:
        await self._crawl_company_reviews(name)
        return await self.get_reviews(name)
        
    except Exception as e:
      print(f"❌ 리뷰 데이터 조회 중 오류 발생: {str(e)}")
      return []
  
  async def _perform_analysis(self, name: str) -> Dict[str, Any]:
    """실제 리뷰 분석 수행"""
    # 리뷰 데이터 조회
    reviews = await self.get_reviews(name)
    
    print(f"📊 '{name}' 리뷰 {len(reviews)}개 분석 시작")
    
    # 현재 실행 중인 이벤트 루프 가져오기
    loop = asyncio.get_event_loop()

    try:
      # 블로킹 방지를 위해 동기 함수를 별도 스레드(executor)에서 실행해 비동기 처리
      # 리뷰 데이터 전처리
      df = await loop.run_in_executor(
        None, self.review_dataset.preprocess_reviews, reviews
      )
      
      # DataFrame이 비어있는지 확인
      if df.empty:
        return self._get_default_response()
      
      print(f"📋 전처리 완료: {len(df)}개 리뷰 항목")
      
      # 리뷰 분석 실행
      analysis_result = await loop.run_in_executor(
        None, self.review_analyzer.analyze_reviews_with_keywords, df
      )
      
      print(f"✅ '{name}' 리뷰 분석 완료")
      return analysis_result
      
    except Exception as e:
      print(f"❌ '{name}' 리뷰 분석 중 오류: {str(e)}")
      return self._get_default_response()
    
  def _get_default_response(self) -> Dict[str, Any]:
    """분석 실패시 기본 응답"""
    return {
      'scored_df': pd.DataFrame(),  # 실제 빈 DataFrame 사용
      'pros': {
        'avg_score': 0.0,
        'keywords': [],
        'sample_reviews': []
      },
      'cons': {
        'avg_score': 0.0,
        'keywords': [],
        'sample_reviews': []
      }
    }
  
  async def clear_analysis_cache(self, company_name: Optional[str] = None) -> int:
    """리뷰 분석 캐시 삭제"""
    try:
      if company_name:
        # 특정 기업의 캐시만 삭제
        cache_key = self._get_cache_key(company_name)
        
        redis_deleted = 0
        
        # Redis에서 삭제
        if redis_client.is_connected and redis_client._redis is not None:
          redis_deleted = await redis_client.delete(cache_key)
        
        return redis_deleted
      else:
        # 모든 리뷰 분석 캐시 삭제
        pattern = "review_analysis:*"
        
        redis_deleted = 0
        
        # Redis에서 패턴 매칭하여 삭제  
        if redis_client.is_connected and redis_client._redis is not None:
          keys = await redis_client.keys(pattern)
          if keys:
            redis_deleted = await redis_client.delete(*keys)
        
        return redis_deleted
        
    except Exception as e:
      print(f"리뷰 분석 캐시 삭제 중 오류: {str(e)}")
      return 0

  async def _crawl_company_reviews(self, company_name: str) -> List[Dict]:
    """TeamBlind에서 기업 리뷰 크롤링"""
    try:
      import sys
      import os
      django_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
      if django_root not in sys.path:
        sys.path.insert(0, django_root)
      
      from crawling.com_review_crawling import CompanyReviewCrawler
      
      if self._review_crawler is None:
        print("새 리뷰 크롤러 인스턴스 생성")
        self._review_crawler = CompanyReviewCrawler()
      else:
        print("기존 리뷰 크롤러 인스턴스 재사용")
      
      # 현재 실행 중인 이벤트 루프 가져오기
      loop = asyncio.get_event_loop()
      
      # 크롤링 실행 (동기 함수를 비동기로 실행)
      crawled_reviews = await loop.run_in_executor(
        None, self._review_crawler.crawl_single_company_reviews, company_name
      )
      
      if crawled_reviews:
        print(f"✅ 크롤링 완료: {len(crawled_reviews)}개 리뷰")
        return await company_review_model.get_reviews_by_company(company_name)
        
    except Exception as e:
      print(f"❌ 리뷰 크롤링 중 오류 발생: {str(e)}")
      return []

  def cleanup_review_crawler(self):
    """리뷰 크롤러 리소스 정리"""
    if self._review_crawler:
      print("리뷰 크롤러 리소스 정리 중...")
      self._review_crawler.close_connection()
      self._review_crawler = None

# 싱글톤 인스턴스
review_analysis_service = ReviewAnalysisService() 