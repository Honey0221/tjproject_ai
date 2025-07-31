from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from ..models.schemas import (
  CompanySearchResponse, 
  CompanyRankingResponse, 
  Company,
  RankingItem,
  ErrorResponse
)
from ..services.search_service import search_service
from datetime import datetime

router = APIRouter(prefix="/companies", tags=["companies"])

@router.get(
  "/search",
  response_model=CompanySearchResponse,
  summary="기업 검색",
  description="기업명 또는 카테고리로 기업을 검색합니다.",
  responses={
    200: {"model": CompanySearchResponse, "description": "검색 성공"},
    400: {"model": ErrorResponse, "description": "잘못된 요청"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def search_companies(
  name: Optional[str] = Query(None, description="검색할 기업명"),
  category: Optional[str] = Query(None, description="검색할 카테고리")
):
  """기업 검색 API"""
  try:
    companies_data = await search_service.search_company_with_cache(
      name=name,
      category=category
    )
    
    # MongoDB 문서를 Pydantic 모델로 변환
    companies = []
    for company_data in companies_data:
      company = Company.from_mongo_doc(company_data)
      companies.append(company)
    
    # 검색 타입과 키워드 결정
    search_type = "카테고리" if category else "이름"
    search_keyword = category if category else name
    
    return CompanySearchResponse(
      search_type=search_type,
      search_keyword=search_keyword,
      total_count=len(companies),
      companies=companies
    )
  except Exception as e:
    print(f"검색 중 에러 발생: {str(e)}")
    raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")

@router.get(
  "/ranking",
  response_model=CompanyRankingResponse,
  summary="기업 재무 랭킹 조회",
  description="연도별 기업 재무 랭킹을 조회합니다 (매출액, 영업이익, 순이익).",
  responses={
    200: {"model": CompanyRankingResponse, "description": "랭킹 조회 성공"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def get_company_ranking(
  year: int = Query(2024, description="조회할 연도", ge=2020, le=2030),
  limit: int = Query(10, description="조회할 기업 수", ge=1, le=50)
):
  """기업 재무 랭킹 조회 API"""
  try:
    rankings_data = await search_service.get_comprehensive_ranking(year, limit)
    
    # 데이터를 Pydantic 모델로 변환
    return CompanyRankingResponse(
      매출액=[
        RankingItem(name=item['name'], amount=item['amount'], year=item['year'])
        for item in rankings_data.get('매출액', [])
      ],
      영업이익=[
        RankingItem(name=item['name'], amount=item['amount'], year=item['year'])
        for item in rankings_data.get('영업이익', [])
      ],
      순이익=[
        RankingItem(name=item['name'], amount=item['amount'], year=item['year'])
        for item in rankings_data.get('순이익', [])
      ]
    )
    
  except Exception as e:
    print(f"랭킹 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"랭킹 조회 중 오류 발생: {str(e)}"
    )

@router.get(
  "/cache/stats",
  summary="기업 관련 캐시 통계",
  description="기업 관련 캐시 시스템의 통계 정보를 조회합니다."
)
async def get_company_cache_stats():
  """기업 캐시 통계 조회 API"""
  try:
    from ..database.redis_client import redis_client
    
    # Redis 캐시에서 기업 관련 키 수 조회
    company_search_keys = 0
    ranking_keys = 0
    
    if redis_client.is_connected and redis_client._redis is not None:
      try:
        search_keys = await redis_client.keys("company_search:*")
        rank_keys = await redis_client.keys("comprehensive_ranking:*")
        company_search_keys = len(search_keys)
        ranking_keys = len(rank_keys)
      except Exception as e:
        print(f"Redis 키 조회 오류: {e}")
    
    stats = {
      "timestamp": datetime.now().isoformat(),
      "company_cache": {
        "company_search_keys": company_search_keys,
        "ranking_keys": ranking_keys,
        "total_keys": company_search_keys + ranking_keys,
        "expire_time_hours": {
          "company_search": 2,
          "ranking": 1
        }
      },
      "redis": {
        "connected": redis_client.is_connected,
        "company_search_keys": company_search_keys,
        "ranking_keys": ranking_keys
      }
    }
    
    return stats
    
  except Exception as e:
    print(f"기업 캐시 통계 조회 중 에러 발생: {str(e)}")
    raise HTTPException(status_code=500, 
    detail=f"기업 캐시 통계 조회 중 오류 발생: {str(e)}"
  )

@router.delete(
  "/cache/clear",
  summary="기업 캐시 초기화",
  description="기업 관련 캐시를 삭제합니다. 특정 패턴만 삭제하거나 전체 삭제 가능합니다."
)
async def clear_company_cache(
  pattern: Optional[str] = Query(
    None, description="삭제할 캐시 키 패턴 (기본값: 전체 삭제)")
):
  """기업 캐시 초기화 API"""
  try:
    cleared_count = await search_service.clear_cache(pattern)
    
    message = f"기업 캐시 정리 완료: {cleared_count}개 항목 삭제"
    if pattern:
      message += f" (패턴: {pattern})"
    else:
      message += " (전체)"
    
    return {
      "message": message,
      "cleared_count": cleared_count,
      "pattern": pattern or "전체",
      "cache_type": "company"
    }
    
  except Exception as e:
    print(f"기업 캐시 초기화 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"기업 캐시 초기화 중 오류 발생: {str(e)}"
    ) 