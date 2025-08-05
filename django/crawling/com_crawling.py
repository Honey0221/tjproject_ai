from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import pymongo
from datetime import datetime
import time
import re
import concurrent.futures
import threading
from driver import company_crawler_driver

class CompanyCrawler:
  def __init__(self, max_workers=4):
    # MongoDB 연결 설정
    self.client = pymongo.MongoClient('mongodb://localhost:27017/')
    self.db = self.client['company_db']
    self.collection = self.db['companies']
    
    # 멀티스레딩 설정
    self.max_workers = max_workers
    
    # 메인 드라이버 (기업 정보 수집용)
    self.driver = company_crawler_driver()
    
    # 단일 크롤링용 재사용 드라이버
    self._single_driver = None

  def _crawl_single_company(self, company_data):
    """단일 기업 크롤링 (스레드에서 실행)"""
    href, company_name, company_idx, total_companies = company_data
    
    try:
      print(f"  {company_idx+1}/{total_companies}: {company_name} 정보 수집 중... (스레드-{threading.current_thread().name})")
      
      # 기업 페이지로 이동
      self.driver.get(href)
      
      # infobox 정보 수집
      company_info = self._extract_company_info(self.driver, company_name)
      
      if company_info:
        print(f"  ✅ {company_idx+1}/{total_companies}: {company_name} 정보 수집 성공")
        return company_info
      else:
        print(f"  ❌ {company_idx+1}/{total_companies}: {company_name} 정보 수집 실패")
        return None
        
    except Exception as e:
      print(f"  ❌ {company_idx+1}/{total_companies}: {company_name} 크롤링 오류 - {e}")
      return None

  def _extract_company_info(self, driver, company_name):
    """기업 정보 추출"""
    # infobox 테이블이 있는지 확인
    infobox_elements = driver.find_elements(By.CSS_SELECTOR, "table.infobox")
    if not infobox_elements:
      print(f"'{company_name}' 페이지에 infobox가 없습니다.")
      return None
    
    infobox_table = infobox_elements[0]
    
    # tbody 안의 모든 tr 요소들 확인
    tbody = infobox_table.find_element(By.TAG_NAME, "tbody")
    tr_elements = tbody.find_elements(By.TAG_NAME, "tr")
    if not tr_elements:
      print(f"'{company_name}' 페이지에 tr 태그가 없습니다.")
      return None
    
    # 기업 정보를 저장할 딕셔너리
    company_info = {}
    
    # tr 요소들에서 정보 추출
    for i, tr in enumerate(tr_elements):
      # th 태그 찾기 (키값)
      th_elements = tr.find_elements(By.TAG_NAME, "th")
      td_elements = tr.find_elements(By.TAG_NAME, "td")
      
      # 첫번째 tr에서는 img src만 가져오기 (로고)
      if i == 0 and td_elements:
        td_element = td_elements[0]
        img_elements = td_element.find_elements(By.TAG_NAME, "img")
        if img_elements:
          img_src = img_elements[0].get_attribute("src")
          if img_src:
            # 상대 경로를 절대 경로로 변환
            if img_src.startswith('//'):
              img_src = 'https:' + img_src
            elif img_src.startswith('/'):
              img_src = 'https://ko.wikipedia.org' + img_src
            company_info['로고'] = img_src
      
      # 나머지 tr
      if th_elements and td_elements:
        # th 태그의 텍스트를 키로 사용
        key = th_elements[0].text.strip()
        
        # td 태그의 텍스트를 값으로 사용 (img 태그 무시)
        td_element = td_elements[0]
        value = td_element.text.strip()
        
        # "본문 참조"인 경우 링크의 href 속성 가져오기
        if value == "본문 참조":
          value = "본문 참조 + https://ko.wikipedia.org/wiki/" + company_name
        
        if key and value:
          company_info[key] = value
      
    # 요약 정보
    summary_paragraphs = driver.find_elements(
      By.CSS_SELECTOR, "div.mw-parser-output > p")
    if summary_paragraphs:
      summary_text = ""
      for p in summary_paragraphs[:3]:  # 첫 3개 문단만
        text = p.text.strip()
        if text:
          # 참조 번호 [1], [2], ... 제거
          text = re.sub(r'\[\d+\]', '', text)
          summary_text += text + "\n\n"
      company_info['summary'] = summary_text.strip()
    else:
      company_info['summary'] = ""

    # 메타 정보 추가
    company_info['name'] = company_name
    company_info['crawled_at'] = datetime.now()
    
    return company_info
      
  def _process_companies_parallel(self, company_links, category_name):
    """기업들을 병렬로 처리"""
    print(f"  → {len(company_links)}개 기업을 {self.max_workers}개 스레드로 병렬 처리 시작")
    
    # 기업 데이터 준비
    company_data_list = []
    for company_idx, (href, company_name) in enumerate(company_links):
      company_data = (href, company_name, company_idx, len(company_links))
      company_data_list.append(company_data)
    
    # 병렬 처리
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
      # 모든 기업 작업 제출
      future_to_company = {
        executor.submit(self._crawl_single_company, company_data): company_data
        for company_data in company_data_list
      }
      
      # 결과 수집
      for future in concurrent.futures.as_completed(future_to_company):
        company_data = future_to_company[future]
        try:
          result = future.result()
          if result:
            results.append(result)
        except Exception as e:
          print(f"  ❌ 스레드 처리 오류: {e}")
    
    print(f"  → {category_name}: {len(results)}/{len(company_links)}개 기업 처리 완료")
    return results

  def get_company_list(self):
    try:
      url = "https://ko.wikipedia.org/wiki/분류:대한민국의_도시별_기업"

      self.driver.get(url)
      time.sleep(2)

      company_info_list = []

      # 첫 번째 단계: 카테고리 페이지에서 모든 하위 카테고리 링크 수집
      category_div = self.driver.find_element(By.CLASS_NAME, "mw-category")
      first_li_elements = category_div.find_elements(By.TAG_NAME, "li")
      
      print(f"첫 번째 단계: 총 {len(first_li_elements)}개의 하위 카테고리를 찾았습니다.")
      
      category_urls = []
      for i, li in enumerate(first_li_elements):
          
        try:
          a_element = li.find_element(By.CSS_SELECTOR, "bdi > a")
          href = a_element.get_attribute("href")
          category_name = a_element.text.strip()
          
          if href and category_name:
            category_urls.append((href, category_name))
            print(f"  {i+1}. {category_name}: {href}")
            
        except Exception as e:
          print(f"첫 번째 단계 li 태그 처리 중 오류: {e}")
          continue
      
      print(f"\n총 {len(category_urls)}개의 카테고리를 처리합니다.")
      
      # 두 번째 단계: 각 카테고리 페이지로 이동하여 실제 기업 페이지들 수집
      for category_idx, (category_url, category_name) in enumerate(category_urls):
          
        print(f"\n=== 카테고리 {category_idx + 1}/{len(category_urls)}: {category_name} 처리 중 ===")
        
        try:
          self.driver.get(category_url)
          time.sleep(2)
          
          # 서울 카테고리인지 확인
          if "서울" in category_name:
            category_results = self._process_seoul_category_with_pagination(category_name)
            company_info_list.extend(category_results)
          else:
            # 기존 방식으로 처리 (단일 페이지)
            category_results = self._process_single_page_category(category_name)
            company_info_list.extend(category_results)
            
        except Exception as e:
          print(f"카테고리 {category_name} 처리 중 오류: {e}")
          continue

      print(f"\n=== 최종 결과: 총 {len(company_info_list)}개 기업의 정보를 수집 완료 ===")
      return company_info_list
      
    except Exception as e:
      print(f"기업 목록 조회 중 오류 발생: {e}")
      return []

  def _process_seoul_category_with_pagination(self, category_name):
    """서울 카테고리의 페이지네이션 처리"""
    all_company_links = []
    current_page = 1
    
    while True:
      try:
        print(f"  📄 {category_name} - 페이지 {current_page} 처리 중...")
        
        # 현재 페이지에서 기업 링크 수집
        page_company_links = self._collect_company_links_from_current_page()
        
        if page_company_links:
          all_company_links.extend(page_company_links)
          print(f"  ✅ 페이지 {current_page}: {len(page_company_links)}개 기업 링크 수집")
        else:
          print(f"  ⚠️ 페이지 {current_page}: 기업 링크를 찾을 수 없습니다.")
        
        # 다음 페이지 버튼 찾기
        next_button = self._find_next_page_button()
        
        if next_button:
          # 다음 페이지로 이동
          self.driver.execute_script("arguments[0].click();", next_button)
          time.sleep(2)
          current_page += 1
        else:
          print(f"  📋 {category_name}: 더 이상 페이지가 없습니다. 총 {current_page}페이지 처리 완료")
          break
          
      except Exception as e:
        print(f"  ❌ 페이지 {current_page} 처리 중 오류: {e}")
        break
    
    print(f"  📊 {category_name}: 총 {len(all_company_links)}개 기업 링크 수집 완료")
    
    # 수집된 모든 기업 링크들을 병렬로 처리
    if all_company_links:
      category_results = self._process_companies_parallel(all_company_links, category_name)
      return category_results
    else:
      return []

  def _collect_company_links_from_current_page(self):
    """현재 페이지에서 기업 링크 수집"""
    company_links = []
    
    try:
      # mw-category div 찾기
      category_div = self.driver.find_element(By.CSS_SELECTOR, "#mw-pages .mw-category")
      li_elements = category_div.find_elements(By.TAG_NAME, "li")
      
      for i, li in enumerate(li_elements):
        try:
          # li 안의 a 태그 찾기
          a_element = li.find_element(By.TAG_NAME, "a")
          href = a_element.get_attribute("href")
          company_name = a_element.text.strip()
          
          if href and company_name:
            company_links.append((href, company_name))
            
        except Exception as e:
          print(f"    기업 링크 수집 중 오류: {e}")
          continue
          
    except NoSuchElementException:
      print(f"    mw-category div를 찾을 수 없습니다.")
      
    return company_links

  def _find_next_page_button(self):
    """다음 페이지 버튼 찾기"""
    try:
      # #mw-pages > a 태그에서 "다음 페이지" 텍스트를 가진 버튼 찾기
      next_buttons = self.driver.find_elements(By.CSS_SELECTOR, "#mw-pages > a")
      
      for button in next_buttons:
        if "다음 페이지" in button.text:
          return button
          
      return None
      
    except Exception as e:
      print(f"    다음 페이지 버튼 찾기 오류: {e}")
      return None

  def _process_single_page_category(self, category_name):
    """단일 페이지 카테고리 처리 (기존 방식)"""
    try:
      # mw-category div 찾기
      category_div = self.driver.find_element(By.CSS_SELECTOR, "#mw-pages .mw-category")
      second_li_elements = category_div.find_elements(By.TAG_NAME, "li")
      
      print(f"{category_name}에서 {len(second_li_elements)}개의 기업을 찾았습니다.")
      
      # 모든 기업 링크 수집
      company_links = []
      for i, li in enumerate(second_li_elements):
          
        try:
          # li 안의 a 태그 찾기
          a_element = li.find_element(By.TAG_NAME, "a")
          href = a_element.get_attribute("href")
          company_name = a_element.text.strip()
          
          if href and company_name:
            company_links.append((href, company_name))
            
        except Exception as e:
          print(f"기업 링크 수집 중 오류: {e}")
          continue
      
      # 수집된 기업 링크들을 병렬로 처리
      category_results = \
        self._process_companies_parallel(company_links, category_name)
          
      print(f"✅ {category_name} 카테고리 처리 완료")
      return category_results
      
    except NoSuchElementException:
      print(f"{category_name}에서 mw-category div를 찾을 수 없습니다.")
      return []

  def save_to_mongodb(self, company_info):
    try:
      # 이름 중복 확인
      existing = self.collection.find_one({
        'name': company_info['name'],
      })
      
      if existing:
        print(f"'{company_info['name']}'의 정보가 이미 존재합니다.")
        self.collection.update_one(
          {'_id': existing['_id']},
          {'$set': company_info}
        )
        print(f"{company_info['name']} 문서 수정 완료")
      else:
        self.collection.insert_one(company_info)
        print("저장 완료")
        
    except Exception as e:
      print(f"MongoDB 저장 중 오류 발생: {e}")
  
  def display_company_names(self, company_info_list):
    company_names = []
    for info in company_info_list:
      name = info.get('name')
      # 소괄호와 그 안의 내용 제거
      clean_name = re.sub(r'\s*\([^)]*\)', '', name).strip()
      company_names.append(clean_name)
    
    return company_names
  
  def _get_or_create_single_driver(self):
    """재사용 가능한 단일 크롤링 드라이버 반환"""
    if self._single_driver is None:
      print("새 드라이버 생성 중...")
      self._single_driver = company_crawler_driver()
    else:
      print("기존 드라이버 재사용")
    return self._single_driver

  def crawl_single_company_by_name(self, company_name: str):
    """
    단일 기업명으로 Wikipedia에서 직접 크롤링
    search_service.py에서 사용하기 위한 메서드
    """
    try:
      driver = self._get_or_create_single_driver()
      
      wikipedia_url = f"https://ko.wikipedia.org/wiki/{company_name}"
      
      driver.get(wikipedia_url)
      time.sleep(1) 
      
      company_info = self._extract_company_info(driver, company_name)
      
      if company_info:
        self.save_to_mongodb(company_info)
        
        # JSON 직렬화 가능한 형태로 변환하여 반환
        serializable_company = {}
        for key, value in company_info.items():
          if key == '_id':
            continue  # _id는 제외
          else:
            # 모든 값을 안전하게 처리
            try:
              import json
              json.dumps(value)
              serializable_company[key] = value
            except:
              # 직렬화 불가능한 값은 문자열로 변환
              serializable_company[key] = str(value)
        
        return serializable_company
      else:
        print(f"❌ '{company_name}' 기업 정보를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
      print(f"❌ '{company_name}' 크롤링 중 오류 발생: {e}")
      return None

  def close_connection(self):
    # 메인 드라이버 종료
    if hasattr(self, 'driver') and self.driver:
      self.driver.quit()
    
    # 단일 크롤링 드라이버 종료
    if self._single_driver:
      self._single_driver.quit()
      self._single_driver = None
    
    # MongoDB 연결 종료
    self.client.close()

if __name__ == "__main__":
  # 멀티스레딩 크롤러 생성 (4개 스레드)
  print("🚀 멀티스레딩 크롤러 시작...")
  crawler = CompanyCrawler(max_workers=4)
  
  try:
    company_info_list = crawler.get_company_list()
    
    # 수집된 기업 이름들만 따로 리스트로 저장
    company_names = crawler.display_company_names(company_info_list)
    print(f"\n📋 수집된 기업 리스트: {company_names}"
          f"  총 {len(company_info_list)}개 기업 정보 수집 완료")
    
    print(f"\n💾 MongoDB 저장 시작...")
    saved_count = 0
    failed_count = 0
    
    for i, company_info in enumerate(company_info_list, 1):
      try:
        print(f"  저장 중... ({i}/{len(company_info_list)})"
              f" {company_info.get('name')}")
        crawler.save_to_mongodb(company_info)
        saved_count += 1
      except Exception as e:
        print(f"  ❌ '{company_info.get('name')}' 저장 실패: {e}")
        failed_count += 1
    
    print(f"\n📊 MongoDB 저장 완료")
    print(f"  ✅ 성공: {saved_count}개")
    print(f"  ❌ 실패: {failed_count}개")
    
  except KeyboardInterrupt:
    print("\n⚠️  사용자가 중단했습니다.")
  except Exception as e:
    print(f"\n❌ 크롤링 중 오류 발생: {e}")
  finally:
    crawler.close_connection()