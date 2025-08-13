import re
import time
import random
from selenium.webdriver.common.by import By
import pymongo
from datetime import datetime
from .driver import company_review_crawler_driver

class CompanyReviewCrawler:
  def __init__(self):
    # MongoDB 연결 설정
    self.client = pymongo.MongoClient('mongodb://localhost:27017/')
    self.db = self.client['company_db']
    self.collection = self.db['company_reviews']

    # 메인 드라이버 (리뷰 수집용)
    self.driver = company_review_crawler_driver()
    
    # 재사용 가능한 드라이버
    self._review_driver = None

  def _get_or_create_review_driver(self):
    """재사용 가능한 리뷰 크롤링 드라이버 반환"""
    if self._review_driver is None:
      print("새 리뷰 드라이버 생성 중...")
      self._review_driver = company_review_crawler_driver()
    else:
      print("기존 리뷰 드라이버 재사용")
    return self._review_driver

  def crawl_single_company_reviews(self, company_name: str):
    """
    단일 기업의 TeamBlind 리뷰 크롤링
    URL: https://www.teamblind.com/kr/company/{company_name}/reviews
    """
    try:
      # 1. 재사용 드라이버 가져오기
      driver = self._get_or_create_review_driver()
      
      # 2. 직접 리뷰 페이지로 이동
      review_url = f"https://www.teamblind.com/kr/company/{company_name}/reviews"
      driver.get(review_url)
      time.sleep(2)
      
      # 3. 리뷰 데이터 추출
      reviews = self._extract_reviews(driver, company_name)
      
      # 4. MongoDB 저장
      self.save_reviews_to_db(reviews)
      
      return reviews
        
    except Exception as e:
      print(f"❌ '{company_name}' 리뷰 크롤링 중 오류 발생: {e}")
      return []

  def _extract_reviews(self, driver, company_name):
    """리뷰 데이터 추출"""
    reviews = []
    
    try:
      # 리뷰 요소 찾기
      review_elements = driver.find_elements(By.CLASS_NAME, "review_item")
      
      if not review_elements:
        print(f"   '{company_name}' 페이지에서 리뷰를 찾을 수 없습니다.")
        return []
      
      for review_element in review_elements:
        # 리뷰 태그 찾기
        parag_element = review_element.find_element(By.CLASS_NAME, "parag")
        p_elements = parag_element.find_elements(By.TAG_NAME, "p")
        
        # 장점 데이터 추출
        pros = ""
        if len(p_elements) > 0:
          try:
            pros_span = p_elements[0].find_element(By.TAG_NAME, "span")
            pros_html = pros_span.get_attribute('innerHTML')
            if pros_html:
              pros = pros_html.replace('<br>', ' ').strip()
              pros = re.sub(r'<[^>]+>', '', pros)
            else:
              pros = pros_span.text.strip()
          except:
            pros = ""
        
        # 단점 데이터 추출
        cons = ""
        if len(p_elements) > 1:
          try:
            cons_span = p_elements[1].find_element(By.TAG_NAME, "span")
            cons_html = cons_span.get_attribute('innerHTML')
            if cons_html:
              cons = cons_html.replace('<br>', ' ').strip()
              cons = re.sub(r'<[^>]+>', '', cons)
            else:
              cons = cons_span.text.strip()
          except:
            cons = ""
        
        review_data = {
          'name': company_name,
          'pros': pros,
          'cons': cons,
          'crawled_at': datetime.now()
        }
        reviews.append(review_data)
            
    except Exception as e:
      print(f"   리뷰 추출 중 오류: {e}")
    
    return reviews

  def load_company_list(self, file_path='company_list.txt'):
    """company_list.txt에서 기업 이름 리스트 가져오기"""
    try:
      with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
        # company_list = [...] 형태에서 리스트 추출
        match = re.search(r'company_list\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
          # 리스트 문자열을 실제 리스트로 변환 
          company_list_str = match.group(1)
          # 따옴표로 둘러싸인 문자열들을 찾아서 리스트로 변환
          companies = re.findall(r"'([^']*)'", company_list_str)
          print(f"기업 리스트 로드 완료: {len(companies)}개 기업")
          return companies
        else:
          print("기업 리스트를 찾을 수 없습니다.")
          return []
    except Exception as e:
      print(f"기업 리스트 로드 중 오류 발생: {e}")
      return []

  def crawl_company_reviews(self, company_name, base_url, driver):
    """특정 기업의 리뷰 크롤링"""
    try:
      driver.get(base_url)
      
      # 검색창 찾기
      try:
        search_elements = driver.find_elements(By.CSS_SELECTOR, ".srch_box input")
        for element in search_elements:
          if element.is_displayed() and element.is_enabled():
            search_input = element
            break
      except Exception as e:
        print(f"  검색창 찾기 시도 실패: {e}")
        time.sleep(2)
      
      # 검색창 클릭
      search_input.click()
      time.sleep(random.uniform(1, 2))
      
      # 기업 이름 입력
      search_input.clear()
      time.sleep(random.uniform(0.5, 1))
      
      # 타이핑 시뮬레이션 (한 글자씩 입력)
      for i, char in enumerate(company_name):
        search_input.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))

      time.sleep(3)
      
      # 검색 실행
      try:
        first_company_item = driver.find_element(
          By.CSS_SELECTOR, ".auto_wp ul.companies li:first-child")
        
        item_name = first_company_item.get_attribute('name')
        if item_name and item_name == company_name:
          first_company_item.click()
          time.sleep(random.uniform(2, 3))
        else:
          print(f" 검색 결과 불일치")
          return []
        
      except Exception as e:
        print(f"  검색 결과 처리 실패: {e}")
        return []
      
      # 해당 기업의 리뷰 페이지로 이동
      try:
        review_links = driver.find_elements(
          By.CSS_SELECTOR, ".inner_wp li.swiper-slide:nth-child(2)")
        if len(review_links) > 0:
          review_links[0].click()
          time.sleep(random.uniform(2, 3))
        else:
          print(f"  리뷰 페이지 링크를 찾을 수 없습니다")
          return []
      except Exception as e:
        print(f"  리뷰 페이지 이동 실패: {e}")
        return []
      
      reviews = []
      
      try:
        review_elements = driver.find_elements(By.CLASS_NAME, "review_item")
        
        for review_element in review_elements:
          # 리뷰 태그 찾기
          parag_element = review_element.find_element(By.CLASS_NAME, "parag")
          p_elements = parag_element.find_elements(By.TAG_NAME, "p")
          
          # 장점 데이터 추출
          pros = ""
          if len(p_elements) > 0:
            try:
              pros_span = p_elements[0].find_element(By.TAG_NAME, "span")
              pros_html = pros_span.get_attribute('innerHTML')
              if pros_html:
                pros = pros_html.replace('<br>', ' ').strip()
                pros = re.sub(r'<[^>]+>', '', pros)
              else:
                pros = pros_span.text.strip()
            except Exception as e:
              print(f"  장점 추출 오류: {e}")
              pros = ""
          
          # 단점 데이터 추출
          cons = ""
          if len(p_elements) > 1:
            try:
              cons_span = p_elements[1].find_element(By.TAG_NAME, "span")
              cons_html = cons_span.get_attribute('innerHTML')
              if cons_html:
                cons = cons_html.replace('<br>', ' ').strip()
                cons = re.sub(r'<[^>]+>', '', cons)
              else:
                cons = cons_span.text.strip()
            except Exception as e:
              print(f"  단점 추출 오류: {e}")
              cons = ""
          
          review_data = {
            'name': company_name,
            'pros': pros,
            'cons': cons,
            'crawled_at': datetime.now()
          }
          reviews.append(review_data)
            
      except Exception as e:
        print(f"  리뷰 수집 중 오류: {e}")
        return []
      
      return reviews
      
    except Exception as e:
      print(f"  전체 크롤링 오류: {e}")
      return []

  def crawl_multiple_companies(self, companies, base_url):
    """여러 기업의 리뷰를 크롤링"""
    print(f"총 {len(companies)}개 기업의 리뷰를 처리 시작")
    
    all_reviews = []
    success_count = 0
    fail_count = 0
    
    for company_idx, company_name in enumerate(companies):
      try:
        print(f"{company_idx+1}/{len(companies)}: {company_name} 처리 중...")
        
        reviews = self.crawl_company_reviews(company_name, base_url, self.driver)
        
        if reviews:
          print(f"  ✅ {company_name} 리뷰 {len(reviews)}개 수집 성공")
          all_reviews.extend(reviews)
          success_count += 1
          
          # 첫 번째 리뷰 바로 출력
          if len(reviews) > 0:
            first_review = reviews[0]
            print(f"\n[샘플 리뷰]\n기업: {first_review['name']}")
            print(f"장점: {first_review['pros']}")
            print(f"단점: {first_review['cons']}\n")
          
        else:
          print(f"  ❌ {company_name} 리뷰 수집 실패")
          fail_count += 1
          
      except Exception as e:
        print(f"  ❌ 크롤링 오류: {e}")
        fail_count += 1
        continue
    
    print(f"\n크롤링 완료: 성공 {success_count}개, 실패 {fail_count}개")
    return all_reviews

  def save_reviews_to_db(self, reviews):
    try:
      if not reviews or len(reviews) == 0:
        print("저장할 리뷰가 없습니다.")
        return
      
      company_name = reviews[0].get('name')
      
      print("=== 리뷰 저장 시작 ===")
      
      # 기업별 리뷰 중복 확인
      existing_reviews = self.collection.find_one({"name": company_name})
      
      if existing_reviews:
        print(f"'{company_name}'의 리뷰가 이미 존재합니다.")
        existing_count = self.collection.count_documents({"name": company_name})
        print(f"기존 리뷰 개수: {existing_count}개")
        print("💡 중복 방지를 위해 저장을 건너뜁니다.")
        return
      else:
        # 새 리뷰 저장
        result = self.collection.insert_many(reviews)
        print(f"💾 '{company_name}' 리뷰 {len(result.inserted_ids)}개 저장 완료")

    except Exception as e:
      print(f"MongoDB 저장 중 오류 발생: {e}")

  def close(self):
    # 리뷰 드라이버 종료
    if self._review_driver:
      quit_start = time.time()
      self._review_driver.quit()
      quit_time = time.time() - quit_start
      print(f"   리뷰 드라이버 종료: {quit_time:.2f}초")
      self._review_driver = None
    
    # MongoDB 연결 종료
    if self.client:
      self.client.close()

if __name__ == "__main__":
  crawler = CompanyReviewCrawler()
  
  try:
    companies = crawler.load_company_list()
    
    base_url = "https://www.teamblind.com/kr/company"

    reviews = crawler.crawl_multiple_companies(companies, base_url)
    
    # 테스트 결과 출력
    print(f"\n=== 크롤링 결과 ===")
    print(f"총 {len(reviews)}개의 리뷰를 수집했습니다.")

    crawler.save_reviews_to_db(reviews)
    
  except Exception as e:
    print(f"크롤링 중 오류 발생: {e}")

  finally:
    crawler.close() 
