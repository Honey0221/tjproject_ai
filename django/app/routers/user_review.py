from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from ..services.user_review_service import user_review_service
from ..schemas.user_review_schema import (
  ReviewCreate, 
  ReviewUpdate, 
  ReviewResponse, 
  ReviewListResponse, 
  ReviewCreateResponse
)

router = APIRouter(prefix="/user_review", tags=["user_review"])

# JWT 검증 의존성 (구현 필요)
async def get_current_user() -> Dict[str, Any]:
  """현재 사용자 정보 조회 (JWT 검증 후)"""
  # TODO: JWT 토큰 검증 로직 구현
  # 임시로 더미 사용자 반환
  return {
    "user_id": 123,
    "email": "user@example.com",
    "nickname": "테스트유저"
  }

@router.post("", response_model=ReviewCreateResponse)
async def create_review(
  review: ReviewCreate,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """
  리뷰 작성
  
  - **companyId**: 기업 ID (필수)
  - **parentId**: 원글 ID (대댓글인 경우)
  - **content**: 리뷰 내용 (1-1000자)
  """
  review_id = await user_review_service.create_review(review, current_user["user_id"])
  
  return ReviewCreateResponse(
    message="리뷰가 성공적으로 작성되었습니다",
    reviewId=review_id
  )

@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
  """
  리뷰 단건 조회
  
  - **review_id**: 조회할 리뷰 ID
  """
  review = await user_review_service.get_review_by_id(review_id)
  if not review:
    raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
  
  return review

@router.put("/{review_id}")
async def update_review(
  review_id: str,
  review: ReviewUpdate,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """
  리뷰 수정 (본인 작성 리뷰만)
  
  - **review_id**: 수정할 리뷰 ID
  - **content**: 수정할 내용 (1-1000자)
  """
  await user_review_service.update_review(review_id, review, current_user["user_id"])
  
  return {"message": "리뷰가 성공적으로 수정되었습니다"}

@router.delete("/{review_id}")
async def delete_review(
  review_id: str,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """
  리뷰 삭제 (본인 작성 리뷰만)
  
  - **review_id**: 삭제할 리뷰 ID
  """
  await user_review_service.delete_review(review_id, current_user["user_id"])
  
  return {"message": "리뷰가 성공적으로 삭제되었습니다"}

@router.get("/{company_id}", response_model=ReviewListResponse)
async def get_company_reviews(company_id: str):
  """
  기업별 리뷰 조회
  
  - **company_id**: 기업 ID
  """

  return await user_review_service.get_reviews_by_company(company_id)

@router.get("/my-reviews", response_model=List[ReviewResponse]) 
async def get_my_reviews(current_user: Dict[str, Any] = Depends(get_current_user)):
  """
  내가 작성한 리뷰 조회
  """
  return await user_review_service.get_reviews_by_user(current_user["user_id"])

@router.get("/{parent_id}/replies", response_model=List[ReviewResponse])
async def get_review_replies(parent_id: str):
  """
  특정 리뷰의 대댓글 조회
  
  - **parent_id**: 부모 리뷰 ID
  """
  return await user_review_service.get_replies_by_parent(parent_id)

@router.post("/{review_id}/like")
async def like_review(
  review_id: str,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """
  리뷰 공감하기/취소하기
  
  - **review_id**: 공감할 리뷰 ID
  """
  result = await user_review_service.like_review(review_id, current_user["user_id"])
  
  return result