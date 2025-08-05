import re
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pymongo
from datetime import datetime

class CompanyReviewCrawler:
  def __init__(self):
    # MongoDB 연결 설정
    self.client = pymongo.MongoClient('mongodb://localhost:27017/')
    self.db = self.client['company_db']
    self.collection = self.db['company_reviews']
    
    self.driver = webdriver.Chrome(options=self._get_chrome_options())

  def _get_chrome_options(self):
    chrome_options = Options()
    
    # 더 강력한 봇 감지 우회 설정
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Cloudflare 우회를 위한 추가 설정
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--disable-features=VizServiceDisplay')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-features=BlinkGenPropertyTrees')
    chrome_options.add_argument('--disable-features=VizHitTestSurfaceLayer')
    chrome_options.add_argument('--disable-features=VizSurfaceDisplay')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    
    # 일반 브라우저처럼 보이게 하는 설정
    chrome_options.add_argument('--disable-extensions-file-access-check')
    chrome_options.add_argument('--disable-extensions-except')
    chrome_options.add_argument('--disable-plugins-discovery')
    chrome_options.add_argument('--disable-preconnect')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    
    # 웹 보안 관련 설정
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-site-isolation-trials')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--ignore-certificate-errors-spki-list')
    
    # 로그 및 에러 메시지 숨기기
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--silent')
    chrome_options.add_argument('--disable-gpu-sandbox')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    # 성능 최적화
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-java')
    chrome_options.add_argument('--disable-dev-tools')
    chrome_options.add_argument('--disable-component-update')
    chrome_options.add_argument('--disable-domain-reliability')
    chrome_options.add_argument('--disable-background-networking')
    
    return chrome_options

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
        first_company_item = driver.find_element(By.CSS_SELECTOR, ".auto_wp ul.companies li:first-child")
        
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
        review_links = driver.find_elements(By.CSS_SELECTOR, ".inner_wp li.swiper-slide:nth-child(2)")
        if len(review_links) > 0:
          review_links[0].click()
          time.sleep(random.uniform(2, 3))
        else:
          print(f"  리뷰 페이지 링크를 찾을 수 없습니다")
          return []
      except Exception as e:
        print(f"  리뷰 페이지 이동 실패: {e}")
        return []
      
      # 리뷰 크롤링
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
      
      print("=== 리뷰 저장 시작 ===")
      # 모든 리뷰를 한 번에 저장 (중복 체크 없이)
      result = self.collection.insert_many(reviews)
      print(f"총 {len(result.inserted_ids)}개 리뷰 저장 완료")
      
      # 기업별 저장 현황 출력
      company_counts = {}
      for review in reviews:
        company_name = review['name']
        company_counts[company_name] = company_counts.get(company_name, 0) + 1
      
      for company, count in company_counts.items():
        print(f"  - {company}: {count}개 리뷰")

    except Exception as e:
      print(f"MongoDB 저장 중 오류 발생: {e}")

  def close(self):
    if self.driver:
      self.driver.quit()
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
