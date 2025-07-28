import uvicorn
import os
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
  sys.path.insert(0, project_root)

if __name__ == "__main__":
  # FastAPI 앱 실행
  uvicorn.run(
    "app.main:app",
    host="localhost",
    port=8000,
    reload=True,  # 개발 모드에서 자동 리로드
    log_level="info"
  ) 