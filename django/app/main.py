from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database.mongodb import mongodb_manager
from .database.redis_client import redis_client
from .database.postgres import tortoise_manager
from .routers import company, review, chatbot, emotion, news, analyze, user_review, system

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
  
  # PostgreSQL (Tortoise ORM) 연결 시도
  await tortoise_manager.connect()
  if tortoise_manager.is_connected:
    print("✅ PostgreSQL 연결 완료")
  else:
    print("⚠️ PostgreSQL 연결 실패 (계속 실행)")
  
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
  
  # PostgreSQL 종료
  if tortoise_manager.is_connected:
    await tortoise_manager.disconnect()
    print("✅ PostgreSQL 연결 종료")
  
  print("👋 FastAPI 애플리케이션 종료!")

# FastAPI 애플리케이션 생성
# lifespan 인자를 사용하여 애플리케이션 시작/종료 시 외부 서비스 연결 상태 확인
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
app.include_router(system.router) 
app.include_router(company.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(user_review.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(emotion.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")