from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from .driver import undetected_driver  # 사용자 정의 우회 드라이버


def get_latest_articles(keyword: str, max_articles: int = 5, headless: bool = True) -> list:
    """
    ✅ 입력된 키워드에 대해 BigKinds 웹사이트에서 최신 뉴스 기사 정보를 크롤링하여 반환합니다.

    Parameters:
    - keyword (str): 검색할 키워드
    - max_articles (int): 수집할 최대 기사 수 (기본값: 5)
    - headless (bool): Chrome 브라우저를 화면에 띄우지 않고 백그라운드에서 실행할지 여부

    Returns:
    - results (list): 크롤링된 뉴스 기사 리스트 (딕셔너리 형태 포함)
    """
    url = "https://www.bigkinds.or.kr/v2/news/index.do"

    # ✅ 우회 및 헤드리스 크롬 드라이버 실행
    driver = undetected_driver(headless=headless)
    wait = WebDriverWait(driver, 10)
    results = []

    try:
        # ✅ BigKinds 메인 페이지 접속
        driver.get(url)

        # ✅ 검색창 로딩 대기
        wait.until(EC.presence_of_element_located((By.ID, "total-search-key")))
        print("✅ 페이지 진입 및 키워드 입력창 확인")

        # ✅ 키워드 입력
        search_input = driver.find_element(By.ID, "total-search-key")
        search_input.clear()
        search_input.send_keys(keyword)

        # ✅ '적용하기' 버튼 클릭 → 검색 수행
        apply_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-search.news-search-btn")
        driver.execute_script("arguments[0].click();", apply_btn)

        # ✅ 검색 결과가 로딩될 때까지 대기
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.news-item")))
        time.sleep(2)  # JS 비동기 처리로 인해 안정적 로딩 확보를 위해 추가 sleep

        # ✅ BeautifulSoup를 통해 페이지 소스 파싱
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        news_items = soup.select('div.news-item')

        # ✅ 기사 목록 순회 (단, 링크가 있는 기사만 최대 max_articles개 수집)
        for item in news_items:
            if len(results) >= max_articles:
                break  # 원하는 기사 수만큼 수집하면 종료

            try:
                # ✅ 링크 정보가 없는 기사는 제외
                link_tag = item.select_one('a.provider')
                if not link_tag or not link_tag.get('href'):
                    continue

                # ✅ 기사 정보 추출
                title = item.select_one('span.title-elipsis').get_text(strip=True)
                summary = item.select_one('p.text').get_text(" ", strip=True)
                press = link_tag.get_text(strip=True)
                link = link_tag['href']

                # 작성자 및 날짜 추출 (항상 2개 존재하는 것은 아니기 때문에 조건부 처리)
                date = item.select('p.name')[0].get_text(strip=True) if len(item.select('p.name')) >= 1 else "N/A"
                writer = item.select('p.name')[1].get_text(strip=True) if len(item.select('p.name')) >= 2 else "N/A"

                # ✅ 결과 리스트에 추가
                results.append({
                    "title": title,
                    "summary": summary,
                    "press": press,
                    "date": date,
                    "writer": writer,
                    "link": link
                })

            except Exception as e:
                print(f"❌ 기사 파싱 오류: {e}")
                continue

    except Exception as e:
        print(f"크롤링 전체 에러: {e}")

    finally:
        driver.quit()  # ✅ 크롬 드라이버 종료 (리소스 정리 필수)

    return results

