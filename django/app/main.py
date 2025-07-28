from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database.mongodb import mongodb_manager
from .database.redis_client import redis_client
from .routers import company, review, chatbot, emotion, news, analyze
from datetime import datetime
from fastapi import HTTPException

@asynccontextmanager
async def lifespan(app: FastAPI):
  """애플리케이션 시작/종료 시 실행되는 이벤트"""
  mongodb_connected = False
  redis_connected = False
  
  # MongoDB 연결 시도
  await mongodb_manager.connect()
  mongodb_connected = mongodb_manager.is_connected
  if mongodb_connected:
    print("✅ MongoDB 연결 완료")
  else:
    print("⚠️ MongoDB 연결 실패 (계속 실행)")
  
  # Redis 연결 시도
  await redis_client.connect()
  redis_connected = redis_client.is_connected
  if redis_connected:
    print("✅ Redis 연결 완료")
  else:
    print("⚠️ Redis 연결 실패 (계속 실행)")
  
  # 개발 모드에서는 외부 서비스 연결 실패와 관계없이 시작
  if settings.dev_mode:
    print("🔧 개발 모드로 FastAPI 애플리케이션 시작!")
  else:
    print("🚀 FastAPI 애플리케이션 시작!")
  
  yield  # 애플리케이션 실행
  
  # 종료 시 연결 정리
  if mongodb_manager.is_connected:
    await mongodb_manager.disconnect()
    print("✅ MongoDB 연결 종료")
  
  if redis_client.is_connected:
    await redis_client.disconnect()
    print("✅ Redis 연결 종료")
  
  print("👋 FastAPI 애플리케이션 종료!")

# FastAPI 애플리케이션 생성
app = FastAPI(lifespan=lifespan)

# CORS 미들웨어 설정
app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.cors_origins,
  allow_credentials=settings.cors_allow_credentials,
  allow_methods=settings.cors_allow_methods,
  allow_headers=settings.cors_allow_headers,
)

# 라우터 등록
app.include_router(company.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(emotion.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")

@app.get(
  "/",
  summary="루트 엔드포인트",
  description="API 상태 확인",
  tags=["root"]
)
async def root():
  """루트 엔드포인트 - API 상태 확인"""
  return {
    "message": f"Welcome to Company Analysis API",
    "status": "running",
    "mode": "development" if settings.dev_mode else "production",
    "external_services": {
      "mongodb": mongodb_manager.is_connected,
      "redis": redis_client.is_connected
    },
    "endpoints": {
      "system": {
        "health_check": "GET /health",
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
        "welcome": "GET /api/chatbot/welcome",
        "action": "POST /api/chatbot/action",
        "company_search": "POST /api/chatbot/search/company",
        "news_search": "POST /api/chatbot/search/news"
      }
    },
    "api_documentation": {
      "swagger_ui": "/docs",
      "redoc": "/redoc",
      "openapi_json": "/openapi.json"
    }
  }

@app.get(
  "/health", 
  summary="시스템 상태 확인",
  description="API 서버의 상태를 확인합니다.",
  tags=["health"]
)
async def health_check():
  """헬스 체크 엔드포인트 - 시스템 상태 및 의존성 확인"""
  health_status = {
    "status": "healthy",
    "timestamp": datetime.now().isoformat(),
    "environment": "development" if settings.dev_mode else "production",
    "services": {}
  }
  
  # MongoDB 연결 상태 확인
  if mongodb_manager.is_connected:
    try:
      await mongodb_manager.client.admin.command('ping')
      health_status["services"]["mongodb"] = {
        "status": "healthy",
        "database": settings.mongodb_db,
        "host": f"{settings.mongodb_host}:{settings.mongodb_port}"
      }
    except Exception as e:
      health_status["services"]["mongodb"] = {
        "status": "unhealthy",
        "error": str(e),
        "database": settings.mongodb_db,
        "host": f"{settings.mongodb_host}:{settings.mongodb_port}"
      }
      if not settings.dev_mode:
        health_status["status"] = "degraded"
  else:
    health_status["services"]["mongodb"] = {
      "status": "disconnected",
      "message": "Not connected (running in development mode)",
      "database": settings.mongodb_db,
      "host": f"{settings.mongodb_host}:{settings.mongodb_port}"
    }
    if not settings.dev_mode:
      health_status["status"] = "degraded"
  
  # Redis 연결 상태 확인
  if redis_client.is_connected:
    try:
      await redis_client.redis.ping()
      health_status["services"]["redis"] = {
        "status": "healthy",
        "host": f"{settings.redis_host}:{settings.redis_port}",
        "db": settings.redis_db
      }
    except Exception as e:
      health_status["services"]["redis"] = {
        "status": "unhealthy", 
        "error": str(e),
        "host": f"{settings.redis_host}:{settings.redis_port}",
        "db": settings.redis_db
      }
      if not settings.dev_mode:
        health_status["status"] = "degraded"
  else:
    health_status["services"]["redis"] = {
      "status": "disconnected",
      "message": "Not connected",
      "host": f"{settings.redis_host}:{settings.redis_port}",
      "db": settings.redis_db
    }
    # Redis가 없으면 캐시 기능이 제한됨
    health_status["status"] = "degraded"
  
  # 머신러닝 모듈 상태 확인
  try:
    from machine_model.company_review.review_dataset import ReviewDataset
    from machine_model.company_review.review_analyzer import ReviewSentimentAnalyzer
    health_status["services"]["machine_learning"] = {
      "status": "healthy",
      "modules": ["ReviewDataset", "ReviewSentimentAnalyzer"]
    }
  except Exception as e:
    health_status["services"]["machine_learning"] = {
      "status": "unhealthy",
      "error": str(e),
      "modules": ["ReviewDataset", "ReviewSentimentAnalyzer"]
    }
    health_status["status"] = "degraded"
  
  # 개발 모드가 아니고 전체 상태가 degraded인 경우에만 HTTP 상태 코드 조정
  if health_status["status"] == "degraded" and not settings.dev_mode:
    from fastapi.responses import JSONResponse
    return JSONResponse(
      status_code=503,
      content=health_status
    )
  
  return health_status

@app.get(
  "/cache", 
  summary="전체 캐시 통계 조회",
  description="모든 캐시 유형의 통계 정보를 반환합니다.",
  tags=["cache", "admin"]
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

@app.get(
  "/cache/backup/status",
  summary="Redis 백업 상태 확인",
  description="현재 진행 중인 백업 작업의 상태를 확인합니다.",
  tags=["cache", "admin"]
)
async def get_backup_status():
  """Redis 백업 상태 조회 API"""
  try:
    if not redis_client.is_connected or redis_client._redis is None:
      raise HTTPException(status_code=503, detail="Redis 서버에 연결되지 않았습니다")
    
    # Redis INFO 명령어로 백업 상태 확인
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

@app.delete(
  "/cache/clear",
  summary="전체 캐시 초기화",
  description="모든 캐시 데이터를 삭제합니다 (기업 검색, 랭킹, 리뷰 분석).",
  tags=["cache", "admin"]
)
async def clear_all_cache():
  """전체 캐시 초기화 API"""
  try:
    if not redis_client.is_connected or redis_client._redis is None:
      raise HTTPException(status_code=503, detail="Redis 서버에 연결되지 않았습니다")
    
    # 전체 Redis DB 초기화
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