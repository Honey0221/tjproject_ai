from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from ..models.schemas import (
  ReviewAnalysisRequest,
  ReviewAnalysisResponse,
  ReviewAnalysisData,
  KeywordItem,
  ReviewSample,
  ErrorResponse
)
from ..services.review_analysis_service import review_analysis_service

router = APIRouter(prefix="/review", tags=["review"])

@router.post(
  "/analyze",
  response_model=ReviewAnalysisResponse,
  summary="리뷰 분석",
  description="기업명을 기반으로 리뷰 감정 분석을 수행합니다.",
  responses={
    200: {"model": ReviewAnalysisResponse, "description": "분석 성공"},
    400: {"model": ErrorResponse, "description": "잘못된 요청"},
    500: {"model": ErrorResponse, "description": "서버 오류"}
  }
)
async def analyze_review(request: ReviewAnalysisRequest):
  """리뷰 분석 API"""
  try:
    # 리뷰 분석 실행
    analysis_result = await review_analysis_service.analysis_review(request.name)
    
    # 분석 결과에서 데이터 추출
    scored_df = analysis_result.get('scored_df')
    pros_data = analysis_result.get('pros')
    cons_data = analysis_result.get('cons')
    
    total_count = 0
    avg_score = 0.0
    
    if scored_df is not None and hasattr(scored_df, 'shape') and not scored_df.empty:
      total_count = scored_df.shape[0] if scored_df.shape[0] > 0 else 0
      if hasattr(scored_df, 'columns') and 'satisfaction_score' in scored_df.columns:
        avg_score = round(scored_df['satisfaction_score'].mean(), 2)
    
    # 장점 데이터 구성
    pros_analysis = ReviewAnalysisData(
      avg_score=pros_data.get('avg_score'),
      keywords=[
        KeywordItem(keyword=kw[0], frequency=kw[1])
        for kw in pros_data.get('keywords')
      ],
      sample_reviews=[
        ReviewSample(
          review=rev['text'] if isinstance(rev, dict) else rev,
          score=rev['score'] if isinstance(rev, dict) else 0.0
        )
        for rev in pros_data.get('sample_reviews', [])
      ]
    )
    
    # 단점 데이터 구성
    cons_analysis = ReviewAnalysisData(
      avg_score=cons_data.get('avg_score'),
      keywords=[
        KeywordItem(keyword=kw[0], frequency=kw[1])
        for kw in cons_data.get('keywords')
      ],
      sample_reviews=[
        ReviewSample(
          review=rev['text'] if isinstance(rev, dict) else rev,
          score=rev['score'] if isinstance(rev, dict) else 0.0
        )
        for rev in cons_data.get('sample_reviews', [])
      ]
    )
    
    return ReviewAnalysisResponse(
      total_count=total_count,
      avg_score=avg_score,
      pros=pros_analysis,
      cons=cons_analysis
    )
    
  except Exception as e:
    print(f"리뷰 분석 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"리뷰 분석 중 오류가 발생했습니다: {str(e)}"
    )

@router.get(
  "/cache/stats",
  summary="리뷰 분석 캐시 통계",
  description="리뷰 분석 캐시 시스템의 통계 정보를 조회합니다."
)
async def get_review_cache_stats():
  """리뷰 분석 캐시 통계 조회 API"""
  try:
    from ..database.redis_client import redis_client
    
    # Redis 캐시에서 리뷰 분석 관련 키 수 조회
    redis_review_keys = 0
    if redis_client.is_connected and redis_client._redis is not None:
      try:
        keys = await redis_client.keys("review_analysis:*")
        redis_review_keys = len(keys)
      except Exception as e:
        print(f"Redis 키 조회 오류: {e}")
    
    return {
      "timestamp": datetime.now().isoformat(),
      "review_analysis_cache": {
        "redis_keys": redis_review_keys,
        "total_keys": redis_review_keys,
        "expire_time_hours": 24
      },
      "redis": {
        "connected": redis_client.is_connected,
        "review_analysis_keys": redis_review_keys
      }
    }
    
  except Exception as e:
    print(f"리뷰 캐시 통계 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"리뷰 캐시 통계 조회 중 오류 발생: {str(e)}"
    )

@router.delete(
  "/cache/clear",
  summary="리뷰 분석 캐시 초기화",
  description="리뷰 분석 캐시를 삭제합니다. 특정 기업만 삭제하거나 전체 삭제 가능합니다."
)
async def clear_review_cache(
  company_name: Optional[str] = Query(
    None, description="삭제할 특정 기업명 (기본값: 전체 삭제)"
  )
):
  """리뷰 분석 캐시 초기화 API"""
  try:
    cleared_count = await review_analysis_service.clear_analysis_cache(company_name)
    
    message = f"리뷰 분석 캐시 정리 완료: {cleared_count}개 항목 삭제"
    if company_name:
      message += f" (기업: {company_name})"
    else:
      message += " (전체)"
    
    return {
      "message": message,
      "cleared_count": cleared_count,
      "company_name": company_name or "전체",
      "cache_type": "review_analysis"
    }
    
  except Exception as e:
    print(f"리뷰 캐시 초기화 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=f"리뷰 캐시 초기화 중 오류 발생: {str(e)}"
    ) 