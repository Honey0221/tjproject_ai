from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from datetime import datetime
from bson import ObjectId
from ..database.mongodb import mongodb_manager
from ..schemas.user_review_schema import (
  ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse
)

class UserReviewService:
  """사용자 리뷰 서비스"""
  def __init__(self):
    self.db_manager = mongodb_manager
  
  @property
  def collection(self):
    """리뷰 컬렉션 반환"""
    if not self.db_manager.is_connected:
      return None
    return self.db_manager.db['user_reviews']
  
  async def _get_review_by_id(self, review_id: str) -> Optional[Dict[str, Any]]:
    """ID로 리뷰 조회"""
    try:
      review = await self.collection.find_one({
        "_id": ObjectId(review_id),
        "deletedAt": None
      })
      
      if review:
        review["id"] = str(review["_id"])
        if review.get("parentId"):
          review["parentId"] = str(review["parentId"])
        del review["_id"]
      
      return review
      
    except Exception as e:
      print(f"리뷰 조회 오류: {str(e)}")
      return None
  
  async def create_review(self, review_data: ReviewCreate, user_id: int) -> str:
    """리뷰 작성"""
    try:
      # 대댓글인 경우 부모 리뷰 존재 여부 확인 및 깊이 자동 계산
      calculated_depth = 0
      if review_data.parentId:
        parent_review = await self._get_review_by_id(review_data.parentId)
        if not parent_review:
          raise HTTPException(status_code=404, detail="부모 리뷰를 찾을 수 없습니다")
        
        # 대댓글 깊이 확인 (최대 2단계까지만 허용)
        parent_depth = parent_review.get("depth", 0)
        
        # 이미 2단계(대댓글)인 경우 더 이상 댓글 작성 불가
        if parent_depth >= 2:
          raise HTTPException(status_code=400, detail="더 이상 댓글을 작성할 수 없습니다")
        
        calculated_depth = parent_depth + 1
      
      # 리뷰 데이터 준비
      review_doc = {
        "userId": user_id,
        "companyId": review_data.companyId,
        "parentId": ObjectId(review_data.parentId) if review_data.parentId else None,
        "content": review_data.content,
        "depth": calculated_depth,  # 자동 계산된 깊이 사용
        "likeCount": 0,
        "likedBy": [],
        "createdAt": datetime.now(),
        "updatedAt": datetime.now(),
        "deletedAt": None
      }
      
      # MongoDB에 저장
      result = await self.collection.insert_one(review_doc)
      return str(result.inserted_id)
        
    except HTTPException:
      raise
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"리뷰 작성 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def get_review_by_id(self, review_id: str) -> Optional[ReviewResponse]:
    """리뷰 단건 조회"""
    try:
      review = await self._get_review_by_id(review_id)
      if not review:
        return None
      
      # 단건 조회는 해당 리뷰 하나만 반환 (대댓글 포함 X)
      review["replies"] = []  # 빈 배열로 초기화
      
      return ReviewResponse(**review)
      
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"리뷰 조회 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def update_review(
    self, review_id: str, review_data: ReviewUpdate, user_id: int) -> bool:
    """리뷰 수정"""
    try:
      # 리뷰 존재 여부 및 권한 확인
      review = await self._get_review_by_id(review_id)
      if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
      
      if review["userId"] != user_id:
        raise HTTPException(status_code=403, detail="리뷰 수정 권한이 없습니다")
      
      # 리뷰 수정
      result = await self.collection.update_one(
        {"_id": ObjectId(review_id), "deletedAt": None},
        {
          "$set": {
            "content": review_data.content,
            "updatedAt": datetime.now()
          }
        }
      )
      
      return True
      
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"리뷰 수정 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def delete_review(self, review_id: str, user_id: int) -> bool:
    """리뷰 삭제"""
    try:
      # 리뷰 존재 여부 및 권한 확인
      review = await self._get_review_by_id(review_id)
      if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
      
      if review["userId"] != user_id:
        raise HTTPException(status_code=403, detail="리뷰 삭제 권한이 없습니다")
      
      result = await self.collection.update_one(
        {"_id": ObjectId(review_id), "deletedAt": None},
        {
          "$set": {
            "deletedAt": datetime.now(),
            "updatedAt": datetime.now()
          }
        }
      )
      
      if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="리뷰 삭제에 실패했습니다")
      
      return True
        
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"리뷰 삭제 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def get_reviews_by_company(self, company_id: str) -> ReviewListResponse:
    """기업별 리뷰 조회 (계층형 구조)"""
    try:
      # 모든 리뷰 조회 (원글 + 대댓글)
      cursor = self.collection.find({
        "companyId": company_id,
        "deletedAt": None
      }).sort("createdAt", -1)
      
      all_reviews = await cursor.to_list(length=None)
      
      # 원글과 대댓글 분류
      main_reviews = []
      replies_map = {}
      
      # ObjectId를 문자열로 변환하고 분류
      for review in all_reviews:
        review["id"] = str(review["_id"])
        if review.get("parentId"):
          review["parentId"] = str(review["parentId"])
          # 대댓글인 경우
          parent_id = review["parentId"]
          if parent_id not in replies_map:
            replies_map[parent_id] = []
          replies_map[parent_id].append(review)
        else:
          # 원글인 경우
          main_reviews.append(review)
        del review["_id"]
      
      # 각 원글에 대댓글 연결 및 정렬
      review_responses = []
      for review in main_reviews:
        review_id = review["id"]
        # 해당 리뷰의 대댓글들을 createdAt 순으로 정렬 (오래된 순)
        replies = replies_map.get(review_id, [])
        replies.sort(key=lambda x: x["createdAt"])
        
        # 대댓글을 ReviewResponse로 변환 (replies는 빈 배열로)
        reply_responses = []
        for reply in replies:
          reply["replies"] = []  # 대댓글의 replies는 빈 배열
          reply_responses.append(ReviewResponse(**reply))
        
        review["replies"] = reply_responses
        review_responses.append(ReviewResponse(**review))
      
      # 전체 원글 리뷰 수 (대댓글 제외)
      total = len(main_reviews)
      
      return ReviewListResponse(total=total, reviews=review_responses)
      
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"기업 리뷰 조회 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def get_reviews_by_user(self, user_id: int) -> List[ReviewResponse]:
    """사용자별 리뷰 조회"""
    try:
      cursor = self.collection.find({
        "userId": user_id,
        "deletedAt": None
      }).sort("createdAt", -1)
      
      reviews = await cursor.to_list(length=None)
      
      # ObjectId를 문자열로 변환
      for review in reviews:
        review["id"] = str(review["_id"])
        if review.get("parentId"):
          review["parentId"] = str(review["parentId"])
        del review["_id"]
      
      return [ReviewResponse(**review) for review in reviews]
      
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"사용자 리뷰 조회 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def get_replies_by_parent(self, parent_id: str) -> List[ReviewResponse]:
    """부모 리뷰의 대댓글 조회"""
    try:
      cursor = self.collection.find({
        "parentId": ObjectId(parent_id),
        "deletedAt": None
      }).sort("createdAt", 1)  # 대댓글은 오래된 순으로
      
      replies = await cursor.to_list(length=None)
      
      # ObjectId를 문자열로 변환
      for reply in replies:
        reply["id"] = str(reply["_id"])
        reply["parentId"] = str(reply["parentId"])
        del reply["_id"]
      
      return [ReviewResponse(**reply) for reply in replies]
      
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"대댓글 조회 중 오류가 발생했습니다: {str(e)}"
      )
  
  async def like_review(self, review_id: str, user_id: int) -> Dict[str, Any]:
    """리뷰 공감/취소"""
    try:
      # 리뷰 존재 여부 확인
      review = await self._get_review_by_id(review_id)
      if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
      
      # 현재 사용자가 이미 공감했는지 확인
      liked_by = review.get("likedBy", [])
      is_already_liked = user_id in liked_by
      
      if is_already_liked:
        # 공감 취소
        result = await self.collection.update_one(
          {"_id": ObjectId(review_id), "deletedAt": None},
          {
            "$pull": {"likedBy": user_id},
            "$inc": {"likeCount": -1},
            "$set": {"updatedAt": datetime.now()}
          }
        )
        action = "unliked"
        message = "공감이 취소되었습니다"
      else:
        # 공감 추가
        result = await self.collection.update_one(
          {"_id": ObjectId(review_id), "deletedAt": None},
          {
            "$addToSet": {"likedBy": user_id},
            "$inc": {"likeCount": 1},
            "$set": {"updatedAt": datetime.now()}
          }
        )
        action = "liked"
        message = "공감이 반영되었습니다"
      
      if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="공감 처리에 실패했습니다")
      
      return {
        "action": action,
        "message": message,
        "isLiked": not is_already_liked
      }
      
    except HTTPException:
      raise
    except Exception as e:
      raise HTTPException(
        status_code=500, 
        detail=f"공감 처리 중 오류가 발생했습니다: {str(e)}"
      )

# 전역 인스턴스
user_review_service = UserReviewService()