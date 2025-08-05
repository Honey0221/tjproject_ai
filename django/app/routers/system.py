from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..config import settings
from ..database.mongodb import mongodb_manager
from ..database.redis_client import redis_client
from ..database.postgres import tortoise_manager

router = APIRouter(tags=["system"])

@router.get(
  "/",
  summary="루트 엔드포인트",
  description="API 상태 확인",
)
async def root():
  """루트 엔드포인트 - API 상태 확인"""
  return {
    "message": f"Welcome to Company Analysis API",
    "status": "running",
    "mode": "development" if settings.dev_mode else "production",
    "external_services": {
      "mongodb": mongodb_manager.is_connected,
      "redis": redis_client.is_connected,
      "postgresql": tortoise_manager.is_connected
    },
    "endpoints": {
      "system": {
        "cache_overview": "GET /cache",
        "cache_backup_status": "GET /cache/backup/status",
        "cache_clear_all": "DELETE /cache/clear"
      },
      "company": {
        "search": "GET /api/companies/search",
        "ranking": "GET /api/companies/ranking",
        "cache_stats": "GET /api/companies/cache/stats",
        "cache_clear": "DELETE /api/companies/cache/clear"
      },
      "review": {
        "analyze": "POST /api/review/analyze",
        "cache_stats": "GET /api/review/cache/stats", 
        "cache_clear": "DELETE /api/review/cache/clear"
      },
      "chatbot": {
        "company_search": "GET /api/chatbot/search/company",
        "news_search": "GET /api/chatbot/search/news",
        "inquiry": "POST /api/chatbot/inquiry"
      },
      "news": {
        "latest_crawl": "POST /api/news/latest",
        "latest_all": "GET /api/news/latest/all", 
        "keywords": "POST /api/news/keywords"
      },
      "user_review": {
        "create": "POST /api/user_review",
        "get": "GET /api/user_review/{review_id}",
        "update": "PUT /api/user_review/{review_id}",
        "delete": "DELETE /api/user_review/{review_id}",
        "company": "GET /api/user_review/company/{company_id}",
        "my_reviews": "GET /api/user_review/my-reviews",
        "replies": "GET /api/user_review/{parent_id}/replies",
        "like": "POST /api/user_review/{review_id}/like"
      },
      "emotion": {
        "analyze": "POST /api/emotion/"
      },
      "analyze": {
        "latest_news": "POST /api/analyze/",
        "filtered_news": "POST /api/analyze/filter",
        "batch_collect": "POST /api/analyze/batch"
      }
    },
    "api_documentation": {
      "swagger_ui": "/docs",
      "redoc": "/redoc",
      "openapi_json": "/openapi.json"
    }
  }

@router.get(
  "/cache", 
  summary="전체 캐시 통계 조회",
  description="모든 캐시 유형의 통계 정보를 반환합니다.",
)
async def get_all_cache_stats():
  """전체 캐시 시스템 통계 - 모든 캐시 유형의 통합 정보"""
  try:
    # Redis 캐시 키 수 조회
    redis_stats = {"connected": redis_client.is_connected, "keys": {}}
    
    if redis_client.is_connected and redis_client._redis is not None:
      # Redis에서 각 캐시 유형별 키 수 조회
      company_keys = await redis_client.keys("company_search:*")
      ranking_keys = await redis_client.keys("comprehensive_ranking:*")  
      review_keys = await redis_client.keys("review_analysis:*")
      
      redis_stats["keys"] = {
        "company_search": len(company_keys),
        "ranking": len(ranking_keys),
        "review_analysis": len(review_keys),
        "total": len(company_keys) + len(ranking_keys) + len(review_keys)
      }
    
    return {
      "timestamp": datetime.now().isoformat(),
      "cache_system_status": {
        "redis_available": redis_client.is_connected
      },
      "cache_expiration_times": {
        "company_search": f"{settings.cache_expire_time}초",
        "ranking": f"{settings.ranking_cache_expire_time}초",
        "review_analysis": f"{settings.review_analysis_cache_expire_time}초"
      },
      "redis_cache": redis_stats,
      "endpoints": {
        "system_cache": {
          "backup_status": "GET /cache/backup/status", 
          "clear_all": "DELETE /cache/clear"
        },
        "domain_cache": {
          "company_stats": "GET /api/companies/cache/stats",
          "company_clear": "DELETE /api/companies/cache/clear",
          "review_stats": "GET /api/review/cache/stats",
          "review_clear": "DELETE /api/review/cache/clear"
        }
      }
    }
    
  except Exception as e:
    print(f"전체 캐시 통계 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"전체 캐시 통계 조회 중 오류 발생: {str(e)}"
    )

@router.get(
  "/cache/backup/status",
  summary="캐시 백업 상태 확인",
  description="현재 진행 중인 백업 작업의 상태를 확인합니다.",
)
async def get_backup_status():
  """캐시 백업 상태 조회 API"""
  try:
    # Redis info 명령어로 백업 상태 확인
    info = await redis_client._redis.info()
    
    return {
      "timestamp": datetime.now().isoformat(),
      "last_save_time": info.get('rdb_last_save_time'),
      "background_save_in_progress": info.get('rdb_bgsave_in_progress') == 1,
      "last_background_save_status": info.get('rdb_last_bgsave_status'),
      "changes_since_last_save": info.get('rdb_changes_since_last_save'),
      "total_saves": info.get('rdb_saves')
    }
    
  except Exception as e:
    print(f"백업 상태 조회 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"백업 상태 조회 중 오류 발생: {str(e)}"
    )

@router.delete(
  "/cache/clear",
  summary="전체 캐시 초기화",
  description="모든 캐시 데이터를 삭제합니다 (기업 검색, 랭킹, 리뷰 분석).",
)
async def clear_all_cache():
  """전체 캐시 초기화 API"""
  try:
    # Redis flushdb 명령어로 전체 캐시 초기화
    result = await redis_client.flushdb()
    
    return {
      "message": "전체 캐시가 초기화되었습니다",
      "success": result,
      "timestamp": datetime.now().isoformat(),
      "cleared_cache_types": ["company_search", "ranking", "review_analysis"]
    }
    
  except Exception as e:
    print(f"전체 캐시 초기화 중 에러 발생: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"전체 캐시 초기화 중 오류 발생: {str(e)}"
    )