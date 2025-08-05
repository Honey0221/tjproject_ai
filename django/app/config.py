from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator
# pydantic이 타입 힌트를 통해 환경 변수를 자동으로 유효성 검사 및 변환 처리해줌

class Settings(BaseSettings):
  # 개발 모드 설정
  dev_mode: bool = True  # 개발 모드에서는 외부 서비스 없이도 실행 가능
  require_external_services: bool = False  # 외부 서비스 연결 필수 여부
  
  # 보안 설정
  allowed_hosts: List[str] = ["*"]
  
  # CORS 설정
  cors_origins: List[str]
  cors_allow_credentials: bool
  cors_allow_methods: List[str] = ["*"]
  cors_allow_headers: List[str] = ["*"]
  
  # MongoDB 설정
  mongodb_host: str
  mongodb_port: int
  mongodb_db: str
  
  # Redis 설정
  redis_host: str
  redis_port: int
  redis_db: int
  
  # PostgreSQL 설정
  postgres_host: str
  postgres_port: int
  postgres_db: str
  postgres_user: str
  postgres_password: str
  
  # 캐시 설정
  cache_expire_time: int
  ranking_cache_expire_time: int
  review_analysis_cache_expire_time: int
  
  # 지역화 설정
  language_code: str = "ko-kr"
  timezone: str = "Asia/Seoul"
  
  # 기본값 파일 경로가 루트에 있는 .env 파일에서 환경변수를 자동으로 읽어옴
  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
  
  @field_validator('cors_origins')
  def parse_cors_origins(cls, v):
    """CORS origins를 문자열에서 리스트로 변환"""
    if isinstance(v, str):
      return [origin.strip() for origin in v.split(',') if origin.strip()]
    return v
  
  @property
  def mongodb_url(self) -> str:
    """MongoDB 연결 URL 생성"""
    return f"mongodb://{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_db}"
  
  @property
  def redis_url(self) -> str:
    """Redis 연결 URL 생성"""
    return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
  
  @property
  def postgres_url(self) -> str:
    """PostgreSQL 연결 URL 생성"""
    return (
      f"postgres://{self.postgres_user}:{self.postgres_password}@"
      f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )
  
  @property
  def tortoise_orm_config(self) -> dict:
    """Tortoise ORM 설정"""
    return {
      "connections": {
        "default": self.postgres_url
      },
      "apps": {
        "models": {
          "models": ["app.models.inquiry"],
          "default_connection": "default",
        },
      },
    }

# 전역 설정 인스턴스
settings = Settings() 