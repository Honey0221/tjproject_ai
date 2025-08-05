import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), './'))

from app.services.search_service import search_service
from app.database.mongodb import mongodb_manager

async def test_company_search():
  print("🔍 기업 검색 테스트")
  print("=" * 50)
  print("MongoDB 연결 및 크롤링 기능을 테스트합니다.")
  print("DB에 있으면 빠르게 조회, 없으면 크롤링합니다.")
  print("=" * 50)
  
  # MongoDB 연결
  try:
    await mongodb_manager.connect()
    print("✅ MongoDB 연결 성공")
  except Exception as e:
    print(f"⚠️ MongoDB 연결 실패: {e}")

  while True:
    try:
      company_name = input("\n검색할 기업명을 입력하세요 (종료: q): ").strip()
      
      if company_name.lower() == 'q':
        print("테스트를 종료합니다.")
        break
      
      print(f"\n🔍 '{company_name}' 검색 중...")
      print("-" * 40)
      
      # 시간 측정 시작
      start_time = time.time()
      
      # 검색 실행
      companies = await search_service.search_company_with_cache(name=company_name)
      
      # 시간 측정 종료
      end_time = time.time()
      execution_time = end_time - start_time
      
      # 결과 출력
      print(f"⏱️ 실행 시간 : {execution_time:.2f}초")
      print(f"📊 결과 개수 : {len(companies)}개")
      
      if companies:
        print("\n✅ 검색 성공!")
        company = companies[0]
        
        # company의 모든 정보 출력
        print("\n📋 기업 정보:")
        print("-" * 30)
        for key, value in company.items():
          # 긴 텍스트는 줄바꿈 처리
          if isinstance(value, str) and len(value) > 100:
            print(f"{key}:")
            print(f"  {value}")
          else:
            print(f"{key}: {value}")
        print("-" * 30)
      else:
        print("❌ 검색 결과 없음")
         
    except Exception as e:
      print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
  try:
    asyncio.run(test_company_search())
  except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
  except Exception as e:
    print(f"실행 오류: {e}")