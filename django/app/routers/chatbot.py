from fastapi import APIRouter, HTTPException
from ..models.schemas import (
  CompanySearchResult, CompanyNewsResult, ErrorResponse, CompanyItem
)
from ..services.search_service import search_service

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.get(
  "/search/company",
  response_model=CompanySearchResult,
  summary="기업 검색 (챗봇용)",
  description="챗봇에서 기업명을 입력받아 검색 결과를 반환합니다.",
  responses={
    200: {"model": CompanySearchResult, "description": "기업 검색 성공"},
    404: {"model": ErrorResponse, "description": "해당 기업의 정보를 찾을 수 없음"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def search_company_for_chatbot(company_name: str):
  """챗봇용 기업 검색 API"""
  try:
    companies = await search_service.search_company_with_cache(
      name=company_name.strip())
    
    # 기업 정보 처리
    company_items = []
    for company in companies[:3]:
      company_name = company.get('name')
      summary = company.get('summary')[:30] + "..."
      
      company_items.append(CompanyItem(
        name=company_name,
        summary=summary
      ))
    
    return CompanySearchResult(
      search_keyword=company_name.strip(),
      companies=company_items
    )
    
  except Exception as e:
    print(f"기업 검색 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"기업 검색 중 오류 발생: {str(e)}"
    )

@router.get(
  "/search/news",
  response_model=CompanyNewsResult,
  summary="뉴스 검색 (챗봇용)",
  description="챗봇에서 기업명을 입력받아 최신 뉴스를 반환합니다.",
  responses={
    200: {"model": CompanyNewsResult, "description": "뉴스 검색 성공"},
    404: {
      "model": ErrorResponse, 
      "description": "기업 정보를 찾을 수 없거나 해당 기업의 뉴스가 없음"
    },
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def search_company_news_for_chatbot(company_name: str):
  """챗봇용 뉴스 검색 API"""
  try:
    return None
  except Exception as e:
    print(f"뉴스 검색 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"뉴스 검색 중 오류 발생: {str(e)}"
    )