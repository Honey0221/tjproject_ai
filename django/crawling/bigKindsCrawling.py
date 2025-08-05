from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import re
from .driver import undetected_driver  # ✅ 우회용 드라이버
import os
from selenium.common.exceptions import TimeoutException
from fastapi import HTTPException

# 설정 상수
WAIT_TIMEOUT = 15
ELEMENT_WAIT_TIMEOUT = 10
# RESULT_FILENAME = "data/result.json"

YEAR = "2025"

# ✅ 매개변수 검증 함수
def validate_parameters(keyword):
    if not keyword or not keyword.strip():
        raise ValueError("검색 키워드는 비어있을 수 없습니다.")

# ✅ 연도 체크박스 클릭 함수
def select_year_checkbox(driver, year=YEAR):
    try:
        wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)
        time.sleep(2)
        checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox'][id^='filter-date-']")
        available_years = [c.get_attribute("value") for c in checkboxes]
        print(f"🔍 선택 가능 연도: {available_years}")

        if year not in available_years:
            print(f"⚠️ '{year}'년은 현재 선택할 수 없습니다.")
            return False

        year_el = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//label[contains(@for, 'filter-date-{year}') or contains(text(), '{year}')]")
        ))
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", year_el)
        print(f"✅ {year}년 체크백스 선택 완료")
        return True
    except Exception as e:
        print(f"❌ 연도 선택 중 오류 발생: {e}")
        return False


def close_popup_safe(driver):
    try:
        wait = WebDriverWait(driver, 5)
        close_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "modal-close")))
        driver.execute_script("arguments[0].click();", close_button)
        try:
            wait_short = WebDriverWait(driver, 2)
            wait_short.until(EC.invisibility_of_element_located((By.CLASS_NAME, "modal-close")))
        except:
            pass
        return True
    except Exception as e:
        if "modal-close" in str(e) or "element not found" in str(e).lower():
            print(f"⚠️ 팝업 닫기 실패: {e}")
        return False

def extract_article_content(driver, article_el, index):
    try:
        wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)

        # ✅ 제목
        try:
            title = article_el.find_element(By.CSS_SELECTOR, ".title-elipsis").text.strip()
        except:
            title = "(제목 없음)"

        # ✅ 언론사 및 링크
        press, link = "(언론사 없음)", "(링크 없음)"
        try:
            press_el = article_el.find_element(By.CSS_SELECTOR, "a.provider")
            press = press_el.text.strip()
            link = press_el.get_attribute("href") or "(링크 없음)"
        except:
            pass

            # ✅ 날짜 및 기자
        date, writer = "(날짜 없음)", "(기자 없음)"
        try:
            date_els = article_el.find_elements(By.CSS_SELECTOR, "p.name")
            if len(date_els) > 0:
                date = date_els[0].text.strip()
            if len(date_els) > 1:
                writer = date_els[1].text.strip()
        except:
            pass

        # ✅ 기사 클릭 및 팝업 추출
        clickable = article_el.find_element(By.CSS_SELECTOR, "a.news-detail")

        # ✅ 이전 popup 내용 가져오기 (stale 방지용 try)
        try:
            popup_el = driver.find_element(By.CLASS_NAME, "news-view-content")
            previous_popup = popup_el.get_attribute("innerHTML")
        except:
            previous_popup = ""

        driver.execute_script("arguments[0].click();", clickable)
        time.sleep(1)

        WebDriverWait(driver, 10).until(
            lambda d: previous_popup != d.find_element(By.CLASS_NAME, "news-view-content").get_attribute("innerHTML")
        )

        content_html = driver.find_element(By.CLASS_NAME, "news-view-content").get_attribute("innerHTML")
        summary = BeautifulSoup(content_html or "", "html.parser").get_text(strip=True)

        if not close_popup_safe(driver):
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except:
                pass

        print(f"{index}. [{date}] {press} - {title}")
        print(f"   ▶ 요약: {summary[:200]}...")
        print(f"   ▶ 기자: {writer}")
        print(f"   ▶ 링크: {link}\n")

        return {
            "title": title,
            "press": press,
            "date": date,
            "writer": writer,
            "summary": summary,
            "link": link
        }

    except Exception as e:
        print(f"⚠️ {index}번째 기사에서 오류 발생: {e}")
        close_popup_safe(driver)
        return None



def search_bigkinds(driver, keyword, unified_category=None, incident_category=None,
                    start_date=None, end_date=None, date_method="manual", period_label=None,  max_articles=None, save_json=True):
    today = datetime.today()

    if not start_date or not end_date:
        start_date = f"{YEAR}-01-01"
        end_date = today.strftime("%Y-%m-%d")

    # ✅ 기준 경로를 현재 파일의 상위 폴더로 설정
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SAVE_DIR = os.path.join(BASE_DIR, "newsCrawlingData")
    os.makedirs(SAVE_DIR, exist_ok=True)
    print("📁 저장 폴더 확인 또는 생성 완료: newsCrawlingData/")

    safe_keyword = re.sub(r'[\\/*?:"<>|]', "_", keyword)
    result_filename = os.path.join(SAVE_DIR, f"{start_date[:4]}_{safe_keyword}_article.json")
    validate_parameters(keyword)

    print("📄 저장될 경로:", result_filename)

    url = "https://www.bigkinds.or.kr/v2/news/index.do"
    articles_data = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        time.sleep(1)
        print("📌 페이지 로딩 완료")

        # ✅ 통합분류 선택
        if unified_category:
            try:
                tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.tab3.search-tab_group")))
                driver.execute_script("arguments[0].click();", tab)
                print("✅ '통합분류' 탭 클릭 완료")
                time.sleep(1)

                categories = unified_category if isinstance(unified_category, (list, tuple)) else [unified_category]

                for category in categories:
                    try:
                        checkbox = wait.until(EC.presence_of_element_located(
                            (By.XPATH, f"//span[normalize-space(text())='{category}']/preceding::input[@type='checkbox'][1]"))
                        )
                        if not checkbox.is_selected():
                            driver.execute_script("arguments[0].click();", checkbox)
                            print(f"✅ '{category}' 체크박스 선택 완료")
                        else:
                            print(f"ℹ️ '{category}'는 이미 선택됨")
                    except Exception as e:
                        print(f"❌ '{category}' 선택 실패: {e}")

            except Exception as e:
                print(f"❌ 통합분류 선택 중 오류: {e}")

        # ✅ 사건사고분류 선택 (incident_category도 복수 가능)
        if incident_category:
            try:
                tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.tab4.search-tab_group")))
                driver.execute_script("arguments[0].click();", tab)
                print("✅ '사건사고분류' 탭 클릭 완료")
                time.sleep(1)

                categories = incident_category if isinstance(incident_category, (list, tuple)) else [incident_category]

                for category in categories:
                    try:
                        checkbox = wait.until(EC.presence_of_element_located(
                            (By.XPATH, f"//span[normalize-space(text())='{category}']/preceding::input[@type='checkbox'][1]"))
                        )
                        if not checkbox.is_selected():
                            driver.execute_script("arguments[0].click();", checkbox)
                            print(f"✅ '{category}' 체크박스 선택 완료")
                        else:
                            print(f"ℹ️ '{category}'는 이미 선택됨")
                    except Exception as e:
                        print(f"❌ '{category}' 선택 실패: {e}")

            except Exception as e:
                print(f"❌ 사건사고분류 선택 중 오류: {e}")

        # ✅ 기간 탭 클릭
        try:
            set_date_filter(
                driver,
                wait,
                method=date_method,
                start_date=start_date,
                end_date=end_date,
                period_label=period_label
            )
        except Exception as e:
            print(f"❌ 날짜 입력 실패: {e}")

        # ✅ 키워드 입력
        try:
            search_input = wait.until(EC.presence_of_element_located((By.ID, "total-search-key")))
            search_input.clear()
            search_input.send_keys(keyword)
            print(f"✅ 키워드 입력 완료: '{keyword}'")
        except Exception as e:
            print(f"❌ 키워드 입력 실패: {e}")

        # ✅ '적용하기' 버튼 클릭
        try:
            # 모든 적용 버튼 가져오기
            apply_buttons = driver.find_elements(By.CSS_SELECTOR, "button.news-search-btn")

            # 텍스트가 '적용하기'인 버튼만 필터링
            apply_btn = None
            for btn in apply_buttons:
                if '적용' in btn.text:
                    apply_btn = btn
                    break

            if apply_btn:
                driver.execute_script("arguments[0].scrollIntoView(true);", apply_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", apply_btn)
                print("✅ '적용하기' 버튼 클릭 완료")
                time.sleep(1)
            else:
                raise Exception("❌ 적용하기 버튼을 찾을 수 없습니다.")

        except Exception as e:
            print(f"❌ 적용하기 버튼 클릭 실패: {e}")


        # ✅ 기사 영역 로딩 대기 및 0건 처리
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.news-inner")))
        except TimeoutException:
            # 기사 없는 경우 처리
            print("⚠️ 뉴스 리스트를 찾을 수 없음. 검색 결과가 없을 가능성 있음.")

            # .no-news나 .no-data 확인
            empty_check = driver.find_elements(By.CSS_SELECTOR, ".no-news, .no-data, .empty-box")
            if empty_check:
                print("⚠️ 검색 결과 없음 - 종료")
                if save_json:
                    with open(result_filename, "w", encoding="utf-8") as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                return []

            # 그래도 없으면 디버깅용 HTML 저장
            with open("debug_page_timeout.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise HTTPException(
                status_code=500,
                detail="❌ 기사 영역이 없고 검색결과도 없음. 사이트 구조 변경 가능성 있음."
            )

        current_page = 1
        consecutive_duplicates = 0
        max_consecutive_duplicates = 4  # 연속 중복 허용 최대치
        collected_keys = set()  # ✅ 중복 방지용
        break_outer = False  # ✅ 외부 루프 종료 플래그

        while (max_articles is None or len(articles_data) < max_articles) and not break_outer:

            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.news-inner")))
            article_elements = driver.find_elements(By.CSS_SELECTOR, "div.news-inner")

            duplicate_count = 0
            idx = 0

            while idx < len(article_elements) and (max_articles is None or len(articles_data) < max_articles):
                try:
                    # ✅ stale 방지: 매 루프마다 elements 새로 가져오기
                    article_elements = driver.find_elements(By.CSS_SELECTOR, "div.news-inner")
                    article_el = article_elements[idx]

                    article_data = extract_article_content(driver, article_el, len(articles_data) + 1)

                    if article_data:
                        duplicate_key = f"{article_data['title']}|{article_data['date']}"

                        if duplicate_key not in collected_keys:
                            articles_data.append(article_data)
                            collected_keys.add(duplicate_key)
                            consecutive_duplicates = 0
                        else:
                            print(f"⚠️ 중복 기사 스킵: {article_data['title']}")
                            consecutive_duplicates += 1
                            if consecutive_duplicates >= max_consecutive_duplicates:
                                print(f"✅ 연속 중복 {consecutive_duplicates}건 감지됨 → 수집 종료")
                                break_outer = True

                    idx += 1

                except Exception as e:
                    print(f"⚠️ {idx + 1}번째 기사 수집 중 오류: {e}")
                    close_popup_safe(driver)
                    idx += 1

                if break_outer:
                    break

            # ✅ 다음 페이지로 이동
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "a.page-next")
                if "disabled" in next_btn.get_attribute("class"):
                    print("✅ 다음 페이지 없음. 수집 종료.")
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                current_page += 1
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ 다음 페이지 이동 실패: {e}")
                break

        # ✅ 결과 저장
        if save_json:
            with open(result_filename, "w", encoding="utf-8") as f:
                json.dump(articles_data, f, ensure_ascii=False, indent=2)
            print(f"✅ {result_filename} 저장 완료 (총 {len(articles_data)}건)")


    except Exception as e:
        print(f"❌ 검색 중 치명적 오류 발생: {e}")
        raise

    return articles_data

def set_date_filter(driver, wait, method="manual", start_date=None, end_date=None, period_label=None):
    try:
        # '기간' 탭 열기
        date_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.search-tab_group[title='Close']")))
        driver.execute_script("arguments[0].click();", date_tab)
        print("✅ '기간' 탭 클릭 완료")
        time.sleep(1)

        if method == "manual":
            driver.execute_script(f"document.getElementById('search-begin-date').value = '{start_date}';")
            driver.execute_script(f"document.getElementById('search-end-date').value = '{end_date}';")
            driver.execute_script("$('#search-begin-date').trigger('change');")
            driver.execute_script("$('#search-end-date').trigger('change');")
            print(f"✅ 날짜 직접 입력 완료: {start_date} ~ {end_date}")


        elif method == "preset":

            try:

                radio = driver.find_element(By.ID, period_label)  # ✅ 이미 프론트에서 "date1-2" 같은 ID값이 옴

                driver.execute_script("arguments[0].click();", radio)

                print(f"✅ '{period_label}' 기간 preset 클릭 완료")

            except Exception as e:

                raise ValueError(f"❌ 날짜 설정 실패: 지원하지 않는 기간 ID: {period_label}")

        else:
            raise ValueError("method는 'manual' 또는 'preset'이어야 합니다.")

        time.sleep(1)

    except Exception as e:
        print(f"❌ 날짜 설정 실패: {e}")


def quick_latest_articles(driver, keyword, max_articles=5):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    url = "https://www.bigkinds.or.kr/v2/news/index.do"
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    time.sleep(1)

    # 키워드 입력
    search_input = wait.until(EC.presence_of_element_located((By.ID, "total-search-key")))
    search_input.clear()
    search_input.send_keys(keyword)
    print(f"🔍 '{keyword}' 입력 완료")

    # 1주일 preset 기간 선택
    date_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.search-tab_group[title='Close']")))
    driver.execute_script("arguments[0].click();", date_tab)
    time.sleep(0.5)
    driver.find_element(By.ID, "date1-2").click()  # '1주' preset
    time.sleep(1)

    # 적용하기 버튼 클릭
    apply_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.news-search-btn")))
    driver.execute_script("arguments[0].click();", apply_btn)
    time.sleep(1)

    # 기사 추출
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.news-inner")))
    article_elements = driver.find_elements(By.CSS_SELECTOR, "div.news-inner")

    articles = []
    for i, el in enumerate(article_elements[:max_articles]):
        try:
            title = el.find_element(By.CSS_SELECTOR, ".title-elipsis").text.strip()
            press = el.find_element(By.CSS_SELECTOR, "a.provider").text.strip()
            link = el.find_element(By.CSS_SELECTOR, "a.provider").get_attribute("href")
            date = el.find_element(By.CSS_SELECTOR, "p.name").text.strip()

            articles.append({
                "title": title,
                "press": press,
                "date": date,
                "link": link
            })
        except Exception as e:
            print(f"⚠️ 기사 {i+1} 수집 실패: {e}")
            continue

    return articles






if __name__ == "__main__":
    driver = None
    try:
        driver = undetected_driver(headless=False)

        # ✅ 사용자 설정
        keyword = "하이브"
        unified_cat = ["사회","국제","IT_과학"]
        incident_cat = None  # 사건사고분류 사용 안함
        start_date = None #"2025-07-19"
        end_date = None #"2025-07-20"

        # "date1-7" > 1일 ,"date1-2" > 1주 , "date1-3" > 1개월, "date1-4" > 3개월, "date1-5" > 6개월 "date1-6" > 1년
        period_label = "date1-2"

        date_method = "preset"
        max_articles = 5

        # ✅ 실행
        search_bigkinds(
            driver,
            keyword=keyword,
            unified_category=unified_cat,
            incident_category=incident_cat,
            start_date=start_date,
            end_date=end_date,
            date_method=date_method,     #manual 수동입력 preset 일, 개월, 년별로 입력
            period_label =period_label,
            max_articles=max_articles,
            save_json=True
        )

        input("🔍 기사 확인 후 Enter를 누르면 브라우저가 닫힌다...")

    except Exception as e:
        print(f"❌ 프로그램 실행 중 오류: {e}")
    finally:
        if driver:
            driver.quit()
            print("✅ 브라우저 종료 완료")
