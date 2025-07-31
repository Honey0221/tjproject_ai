from fastapi import APIRouter, HTTPException
from ..models.schemas import (
  CompanySearchResult, CompanyNewsResult, ErrorResponse, CompanyItem
)
from ..schemas.chatbot_schema import InquiryRequest, InquiryResponse
from ..services.search_service import search_service
from ..database.postgres_models import Inquiry

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
      summary = company.get('summary')[:30]
      if len(summary) < 30:
        summary = summary + "..."
      
      company_items.append(CompanyItem(
        name=company_name,
        summary=summary
      ))
    
    return CompanySearchResult(
      search_keyword=company_name.strip(),
      companies=company_items
    )
    
  except Exception as e:
    print(f"챗봇 기업 검색 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"챗봇 기업 검색 중 오류 발생: {str(e)}"
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

@router.post(
  "/inquiry",
  response_model=InquiryResponse,
  summary="문의하기",
  description="챗봇에서 사용자 문의를 받아 PostgreSQL에 저장합니다.",
  responses={
    200: {"model": InquiryResponse, "description": "문의 등록 성공"},
    400: {"model": ErrorResponse, "description": "잘못된 요청 데이터"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def create_inquiry(inquiry: InquiryRequest):
  """챗봇 문의하기 API"""
  try:
    # Tortoise ORM을 사용해 문의사항 생성
    await Inquiry.create_inquiry(
      inquiry_type=inquiry.inquiry_type,
      inquiry_content=inquiry.inquiry_content
    )
    
    return InquiryResponse(
      message="문의사항이 성공적으로 등록되었습니다. 빠른 시일 내에 답변드리겠습니다."
    )
    
  except Exception as e:
    print(f"문의하기 처리 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"문의하기 처리 중 오류 발생: {str(e)}"
    )