from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..schemas.chatbot_schema import InquiryListResponse, InquiryItem
from ..schemas.common_schema import ErrorResponse
from ..models.inquiry import Inquiry

router = APIRouter(prefix="/inquiry", tags=["inquiry"])

@router.get(
  "/",
  response_model=InquiryListResponse,
  summary="문의사항 목록 조회",
  description="문의사항을 조회합니다. 쿼리 파라미터로 필터링 및 정렬 가능합니다.",
  responses={
    200: {"model": InquiryListResponse, "description": "문의사항 목록 조회 성공"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def get_inquiries(
  type: Optional[str] = Query(None, description="문의 유형 필터링"),
  order: Optional[str] = Query("desc", description="작성일자 정렬")
):
  """문의사항 조회 API"""
  try:
    # 정렬 순서(기본 내림차순)
    order_by = "-created_at" if order == "desc" else "created_at"
    
    if type:
      # 필터링
      inquiries = await Inquiry.filter(inquiry_type=type).order_by(order_by)
    else:
      # 전체 조회
      inquiries = await Inquiry.all().order_by(order_by)
    
    inquiry_items = []
    for inquiry in inquiries:
      inquiry_items.append(InquiryItem(
        id=inquiry.id,
        user_name=inquiry.user_name,
        inquiry_title=inquiry.inquiry_title,
        inquiry_type=inquiry.inquiry_type,
        inquiry_content=inquiry.inquiry_content,
        created_at=inquiry.created_at
      ))
    
    return InquiryListResponse(
      inquiries=inquiry_items
    )
    
  except Exception as e:
    print(f"문의사항 목록 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"문의사항 목록 조회 중 오류 발생: {str(e)}"
    )