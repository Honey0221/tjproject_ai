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

@router.post(
  "", 
  response_model=ReviewCreateResponse,
  summary="리뷰 작성",
  description="새로운 리뷰를 작성합니다. 원글 작성 또는 기존 리뷰에 대한 대댓글 작성이 가능합니다."
)
async def create_review(
  review: ReviewCreate,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """리뷰 작성"""
  review_id = await user_review_service.create_review(review, current_user["user_id"])
  
  return ReviewCreateResponse(
    message="리뷰가 성공적으로 작성되었습니다",
    reviewId=review_id
  )

@router.get(
  "/{review_id}", 
  response_model=ReviewResponse,
  summary="리뷰 단건 조회",
  description="리뷰 ID를 통해 특정 리뷰 하나의 정보만 조회합니다."
)
async def get_review(review_id: str):
  """리뷰 단건 조회"""
  review = await user_review_service.get_review_by_id(review_id)
  if not review:
    raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
  
  return review

@router.put(
  "/{review_id}",
  summary="리뷰 수정",
  description="본인이 작성한 리뷰의 내용을 수정합니다."
)
async def update_review(
  review_id: str,
  review: ReviewUpdate,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """리뷰 수정"""
  await user_review_service.update_review(review_id, review, current_user["user_id"])
  
  return {"message": "리뷰가 성공적으로 수정되었습니다"}

@router.delete(
  "/{review_id}",
  summary="리뷰 삭제",
  description="본인이 작성한 리뷰를 삭제합니다."
)
async def delete_review(
  review_id: str,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """리뷰 삭제"""
  await user_review_service.delete_review(review_id, current_user["user_id"])
  
  return {"message": "리뷰가 성공적으로 삭제되었습니다"}

@router.get(
  "/company/{company_id}", 
  response_model=ReviewListResponse,
  summary="기업별 리뷰 조회",
  description="특정 기업에 대한 모든 리뷰와 대댓글을 계층형 구조로 조회합니다."
)
async def get_company_reviews(company_id: str):
  """기업별 리뷰 조회"""
  return await user_review_service.get_reviews_by_company(company_id)

@router.get(
  "/my-reviews",
  response_model=List[ReviewResponse],
  summary="내 리뷰 조회 (관리자 페이지용)",
  description="현재 로그인한 사용자가 작성한 모든 리뷰를 조회합니다."
)
async def get_my_reviews(current_user: Dict[str, Any] = Depends(get_current_user)):
  """내 리뷰 조회 (관리자 페이지용)"""
  return await user_review_service.get_reviews_by_user(current_user["user_id"])

@router.get("/{parent_id}/replies",
  response_model=List[ReviewResponse],
  summary="대댓글 조회",
  description="특정 리뷰에 달린 모든 대댓글을 조회합니다."
)
async def get_review_replies(parent_id: str):
  """특정 리뷰의 대댓글 조회"""
  return await user_review_service.get_replies_by_parent(parent_id)

@router.post("/{review_id}/like",
  summary="리뷰 공감하기/취소하기",
  description="리뷰에 토글 형식으로 공감 표시하거나 취소합니다."
)
async def like_review(
  review_id: str,
  current_user: Dict[str, Any] = Depends(get_current_user)
):
  """리뷰 공감하기/취소하기"""
  return await user_review_service.like_review(review_id, current_user["user_id"])