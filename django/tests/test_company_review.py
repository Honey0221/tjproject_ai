import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), './'))

from crawling.com_review_crawling import CompanyReviewCrawler
from app.database.mongodb import mongodb_manager

async def test_company_review():
  print("🔍 기업 리뷰 크롤링 테스트")
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

  # 크롤러 인스턴스 생성
  crawler = CompanyReviewCrawler()
  
  while True:
    try:
      company_name = input("\n검색할 기업명을 입력하세요 (종료: q): ").strip()
      
      if company_name.lower() == 'q':
        print("테스트를 종료합니다.")
        break
      
      print(f"\n🔍 '{company_name}' 리뷰 검색 중...")
      print("-" * 40)
      
      # 시간 측정 시작
      start_time = time.time()
      
      # 1. DB에서 리뷰 조회
      reviews = []
      if mongodb_manager.is_connected:
        try:
          collection = mongodb_manager.db['company_reviews']
          cursor = collection.find({"name": company_name})
          reviews = await cursor.to_list(length=None)
        except Exception as e:
          print(f"DB 조회 중 오류: {e}")
      
      if reviews:
        # DB에서 조회 성공
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️ 실행 시간 : {execution_time:.2f}초")
        print(f"📊 조회된 리뷰 : {len(reviews)}개")
        
        print("\n✅ 리뷰 조회 성공!")
        
        # 첫 번째 리뷰 샘플 출력
        if len(reviews) > 0:
          first_review = reviews[0]
          print("\n📋 리뷰 샘플:")
          print("-" * 30)
          print(f"기업명: {first_review.get('name', '')}")
          print(f"장점: {first_review.get('pros', '')[:100]}...")
          print(f"단점: {first_review.get('cons', '')[:100]}...")
          print(f"수집일: {first_review.get('crawled_at', '')}")
          print("-" * 30)
        
        print("📂 데이터 소스: DATABASE (빠른 조회)")
        
      else:
        # DB에 없어서 크롤링 실행
        print(f"🔍 DB에 '{company_name}' 리뷰가 없어 TeamBlind 크롤링을 시작합니다...")
        
        # 리뷰 크롤링 실행
        crawled_reviews = crawler.crawl_single_company_reviews(company_name)
        
        # 시간 측정 종료
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️ 실행 시간 : {execution_time:.2f}초")
        print(f"📊 크롤링된 리뷰 : {len(crawled_reviews)}개")
        
        if crawled_reviews:
          print("\n✅ 리뷰 크롤링 및 저장 성공!")
          
          # 첫 번째 리뷰 샘플 출력
          first_review = crawled_reviews[0]
          print("\n📋 크롤링된 리뷰 샘플:")
          print("-" * 30)
          print(f"기업명: {first_review.get('name', '')}")
          print(f"장점: {first_review.get('pros', '')[:100]}...")
          print(f"단점: {first_review.get('cons', '')[:100]}...")
          print(f"수집일: {first_review.get('crawled_at', '')}")
          print("-" * 30)
          
          print("🕷️ 데이터 소스: CRAWLING (TeamBlind에서 크롤링)")
      
      print("=" * 50)
        
    except Exception as e:
      print(f"❌ 오류 발생: {e}")
  
  # 크롤러 리소스 정리
  try:
    crawler.close()
    print("✅ 크롤러 리소스 정리 완료")
  except:
    pass
  
  # MongoDB 연결 종료
  try:
    await mongodb_manager.disconnect()
    print("✅ MongoDB 연결 종료")
  except:
    pass

if __name__ == "__main__":
  try:
    asyncio.run(test_company_review())
  except KeyboardInterrupt:
    print("\n프로그램을 종료합니다.")
  except Exception as e:
    print(f"실행 오류: {e}")