import hashlib
import json
import re
from typing import Any
from ..models.company import company_model
from ..database.redis_client import redis_client
from ..config import settings

class FinancialDataParser:
  @staticmethod
  def parse_financial_amount(amount_str):
    """재무 금액 문자열을 파싱하여 원 단위 금액과 연도를 반환"""
    try:
      # 연도 추출
      year_match = re.search(r'\((\d{4})년?\)', amount_str)
      year = int(year_match.group(1)) if year_match else None
      
      # 금액 부분 추출 (괄호 앞부분)
      amount_part = amount_str.split('(')[0].strip()
      
      # 숫자와 단위 추출
      amount = 0.0
      
      # 조 단위 처리
      trillion_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*조', amount_part)
      if trillion_match:
        amount += float(trillion_match.group(1).replace(',', '')) * 1000000000000
      
      # 억 단위 처리
      billion_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*억', amount_part)
      if billion_match:
        amount += float(billion_match.group(1).replace(',', '')) * 100000000
      
      # 만 단위 처리
      million_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*만', amount_part)
      if million_match:
        amount += float(million_match.group(1).replace(',', '')) * 10000
      
      # 원 단위 처리 (단위가 없는 숫자)
      if amount == 0.0:
        # 단위가 없는 경우 원 단위로 처리
        number_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', amount_part)
        if number_match:
          amount = float(number_match.group(1).replace(',', ''))
      
      return amount, year
      
    except (ValueError, AttributeError) as e:
      print(f"재무 데이터 파싱 중 오류 발생: {str(e)}")
      return 0.0, None

class SearchService:
  """Redis 전용 비동기 검색 서비스"""
  def __init__(self):
    self.parser = FinancialDataParser()
    self._crawler = None  # 재사용 가능한 크롤러 인스턴스
  
  def _get_cache_key(self, prefix, keyword):
    """캐시 키 생성"""
    keyword_hash = hashlib.md5(keyword.encode()).hexdigest()
    return f"{prefix}:{keyword_hash}"
  
  async def _get_from_cache(self, key: str) -> Any:
    """Redis 캐시에서 값 조회"""
    try:
      if redis_client.is_connected and redis_client._redis is not None:
        value = await redis_client.get(key)
        if value is not None:
          # JSON 파싱 시도
          try:
            return json.loads(value)
          except json.JSONDecodeError:
            return value
      return None
      
    except Exception as e:
      print(f"캐시 조회 오류: {e}")
      return None
  
  async def _set_to_cache(self, key: str, value: Any, expire_seconds: int) -> bool:
    """Redis 캐시에 값 저장"""
    try:
      if redis_client.is_connected and redis_client._redis is not None:
        if isinstance(value, (dict, list)):
          redis_value = json.dumps(value, ensure_ascii=False)
        else:
          redis_value = value
        
        success = await redis_client.setex(key, expire_seconds, redis_value)
        if success:
          print(f"💾 Redis 캐시 저장 성공: {key}")
        return success
      return False
      
    except Exception as e:
      print(f"Redis 캐시 저장 오류: {str(e)}")
      return False
  
  async def search_company_with_cache(self, name=None, category=None, cache_time=None):
    """Redis 캐시를 활용한 기업 검색 (DB에 없으면 자동 크롤링)"""
    cache_time = settings.cache_expire_time
    
    # 검색 키워드 결정
    if category:
      search_keyword = f"category:{category}"
      search_type = "category"
    else:
      search_keyword = f"name:{name if name else ''}"
      search_type = "name"
    
    cache_key = self._get_cache_key("company_search", search_keyword)
    
    # MongoDB에서 검색
    try:
      if search_type == "category":
        companies = await company_model.get_companies_by_category(category)
      else:
        companies = await company_model.get_companies_by_name(name) if name else []
      
      # 결과가 있으면 기존 방식으로 처리
      if companies:
        # 결과를 JSON 직렬화 가능한 형태로 변환
        serializable_companies = []
        for company in companies:
          serializable_company = {}
          for key, value in company.items():
            if key == '_id':
              serializable_company['id'] = str(value)
            else:
              # 모든 값을 안전하게 처리
              try:
                # JSON 직렬화 테스트
                json.dumps(value)
                serializable_company[key] = value
              except:
                # 직렬화 불가능한 값은 문자열로 변환
                serializable_company[key] = str(value)
          serializable_companies.append(serializable_company)
        
        # Redis 캐시에 저장
        await self._set_to_cache(cache_key, serializable_companies, cache_time)
        
        return serializable_companies
      
      # 결과가 없고 이름으로 검색한 경우
      elif search_type == "name" and name and name.strip():
        # 크롤링 진행
        crawled_company = await self._crawl_company_from_wikipedia(name.strip())
        
        if crawled_company:
          # 크롤링된 데이터를 리스트로 감싸서 반환
          serializable_companies = [crawled_company]
          
          # Redis 캐시에 저장
          await self._set_to_cache(cache_key, serializable_companies, cache_time)
          
          return serializable_companies
      
      # 크롤링 실패한 경우
      return []
      
    except Exception as e:
      print(f"검색 중 오류 발생: {str(e)}")
      return []
  
  async def _crawl_company_from_wikipedia(self, company_name: str):
    """Wikipedia에서 기업 정보 크롤링"""
    try:
      # 임포트는 함수 내부에서 수행 (순환 임포트 방지)
      import sys
      import os
      
      # Django 프로젝트 루트 경로를 sys.path에 추가
      django_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
      if django_root not in sys.path:
        sys.path.insert(0, django_root)
      
      from crawling.com_crawling import CompanyCrawler
      
      # 크롤러 인스턴스 재사용
      if self._crawler is None:
        print("새 크롤러 인스턴스 생성")
        self._crawler = CompanyCrawler()
      else:
        print("기존 크롤러 인스턴스 재사용")
      
      # 단일 기업 크롤링 실행
      company_info = self._crawler.crawl_single_company_by_name(company_name)
      
      return company_info
      
    except Exception as e:
      print(f"크롤링 중 오류 발생: {str(e)}")
      return None
  
  async def get_top_companies_by_field(self, field_name, year=None, limit=10):
    """특정 필드 기준 상위 기업 조회"""
    try:
      # MongoDB에서 해당 필드가 있는 모든 기업 조회
      companies = await company_model.get_companies_by_field(field_name)
      
      # 재무 데이터 파싱 및 필터링
      parsed_companies = []
      for company in companies:
        financial_data = company.get(field_name, "")
        amount, data_year = self.parser.parse_financial_amount(financial_data)
        
        # 연도 필터링
        if data_year == year:
          company_data = {
            'name': company.get('name', ''),
            'amount': amount,
            'year': data_year
          }
          parsed_companies.append(company_data)
      
      # 금액 기준 정렬 (내림차순)
      parsed_companies.sort(key=lambda x: x['amount'], reverse=True)
      
      # 상위 기업 반환
      return parsed_companies[:limit]
      
    except Exception as e:
      print(f"{field_name} 기준 상위 기업 조회 중 오류 발생: {str(e)}")
      return []

  async def get_comprehensive_ranking(self, year=2024, limit=10, cache_time=None):
    """연도별 종합 재무 랭킹 조회 (매출액, 영업이익, 순이익)"""
    if cache_time is None:
      cache_time = settings.ranking_cache_expire_time
    
    cache_key = self._get_cache_key("comprehensive_ranking", f"{year}_{limit}")
    
    # 캐시에서 조회
    cached_result = await self._get_from_cache(cache_key)
    if cached_result:
      return cached_result
    
    try:
      # 각 필드별 랭킹 조회
      rankings = {
        '매출액': await self.get_top_companies_by_field('매출액', year, limit),
        '영업이익': await self.get_top_companies_by_field('영업이익', year, limit),
        '순이익': await self.get_top_companies_by_field('순이익', year, limit)
      }
      
      # Redis 캐시에 저장
      await self._set_to_cache(cache_key, rankings, cache_time)
      
      return rankings
      
    except Exception as e:
      print(f"랭킹 조회 중 오류 발생: {str(e)}")
      return {
        '매출액': [],
        '영업이익': [],
        '순이익': []
      }

  async def clear_cache(self, pattern=None):
    """Redis 캐시 초기화"""
    cleared = 0
    
    try:
      # Redis 캐시 삭제
      if redis_client.is_connected and redis_client._redis is not None:
        if pattern:
          keys = await redis_client.keys(pattern)
          if keys:
            cleared = await redis_client.delete(*keys)
        else:
          result = await redis_client.flushdb()
          cleared = 1 if result else 0
        
        if cleared > 0:
          print(f"🗑️ Redis 캐시 삭제: {cleared}개")
      
      return cleared
        
    except Exception as e:
      print(f"캐시 초기화 중 오류 발생: {str(e)}")
      return 0

  def cleanup_crawler(self):
    """크롤러 리소스 정리"""
    if self._crawler:
      print("크롤러 리소스 정리 중...")
      self._crawler.close_connection()
      self._crawler = None

# 싱글톤 인스턴스
search_service = SearchService()