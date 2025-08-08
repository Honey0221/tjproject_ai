from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..schemas.chatbot_schema import InquiryListResponse, InquiryItem
from ..schemas.common_schema import ErrorResponse
from ..models.inquiry import Inquiry

router = APIRouter(prefix="/inquiries", tags=["inquiries"])

@router.get(
  "/",
  response_model=InquiryListResponse,
  summary="전체 문의사항 목록 조회",
  description="모든 문의사항을 최신순으로 조회합니다. limit으로 개수 제한 가능합니다.",
  responses={
    200: {"model": InquiryListResponse, "description": "문의사항 목록 조회 성공"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def get_all_inquiries(limit: Optional[int] = Query(20, description="조회할 문의사항 개수", ge=1, le=100)):
  """전체 문의사항 목록 조회 API"""
  try:
    inquiries = await Inquiry.get_recent(limit=limit)
    total_count = await Inquiry.all().count()
    
    inquiry_items = []
    for inquiry in inquiries:
      inquiry_items.append(InquiryItem(
        id=inquiry.id,
        inquiry_type=inquiry.inquiry_type,
        inquiry_content=inquiry.inquiry_content,
        created_at=inquiry.created_at
      ))
    
    return InquiryListResponse(
      inquiries=inquiry_items,
      total_count=total_count
    )
    
  except Exception as e:
    print(f"문의사항 목록 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"문의사항 목록 조회 중 오류 발생: {str(e)}"
    )

@router.get(
  "/type/{inquiry_type}",
  response_model=InquiryListResponse,
  summary="유형별 문의사항 조회",
  description="특정 유형의 문의사항을 최신순으로 조회합니다.",
  responses={
    200: {"model": InquiryListResponse, "description": "유형별 문의사항 조회 성공"},
    404: {"model": ErrorResponse, "description": "해당 유형의 문의사항이 없음"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def get_inquiries_by_type(inquiry_type: str):
  """유형별 문의사항 조회 API"""
  try:
    inquiries = await Inquiry.get_by_type(inquiry_type=inquiry_type)
    
    if not inquiries:
      raise HTTPException(
        status_code=404,
        detail=f"'{inquiry_type}' 유형의 문의사항을 찾을 수 없습니다."
      )
    
    inquiry_items = []
    for inquiry in inquiries:
      inquiry_items.append(InquiryItem(
        id=inquiry.id,
        inquiry_type=inquiry.inquiry_type,
        inquiry_content=inquiry.inquiry_content,
        created_at=inquiry.created_at
      ))
    
    return InquiryListResponse(
      inquiries=inquiry_items,
      total_count=len(inquiry_items)
    )
    
  except HTTPException:
    raise
  except Exception as e:
    print(f"유형별 문의사항 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"유형별 문의사항 조회 중 오류 발생: {str(e)}"
    )

@router.get(
  "/recent",
  response_model=InquiryListResponse,
  summary="최근 문의사항 조회",
  description="최근 등록된 문의사항을 조회합니다.",
  responses={
    200: {"model": InquiryListResponse, "description": "최근 문의사항 조회 성공"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def get_recent_inquiries(limit: Optional[int] = Query(10, description="조회할 문의사항 개수", ge=1, le=50)):
  """최근 문의사항 조회 API"""
  try:
    inquiries = await Inquiry.get_recent(limit=limit)
    
    inquiry_items = []
    for inquiry in inquiries:
      inquiry_items.append(InquiryItem(
        id=inquiry.id,
        inquiry_type=inquiry.inquiry_type,
        inquiry_content=inquiry.inquiry_content,
        created_at=inquiry.created_at
      ))
    
    return InquiryListResponse(
      inquiries=inquiry_items,
      total_count=len(inquiry_items)
    )
    
  except Exception as e:
    print(f"최근 문의사항 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"최근 문의사항 조회 중 오류 발생: {str(e)}"
    )