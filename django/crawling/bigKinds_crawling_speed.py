import os
import re
import time
import math
from datetime import datetime
from multiprocessing import Pool, cpu_count, freeze_support
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from collections import Counter
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)

from driver import undetected_driver  # ✅ 사용자 정의 우회 드라이버 (필수)

from app.database.db.crawling_database import get_existing_keys, find_summary_any_model
from app.database.db.crawling_database import find_existing_article



# ---------------------------
# 공통 유틸
# ---------------------------
def apply_speed_up(driver):
    """이미지/폰트 등 리소스 로딩 차단 (Chromium 계열에서만 동작)"""
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setBlockedURLs", {
            "urls": ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.woff", "*.ttf", "*.webp", "*.mp4", "*.avi"]
        })
    except Exception:
        pass

def safe_text(el):
    try:
        return el.text.strip()
    except:
        return ""

def parse_total_articles_from_html(html):
    """
    페이지 소스에서 '총 12,345건' 같은 문자열을 찾아 총 건수 반환
    """
    # 수정된 버전 (다양한 문구 커버)
    m = re.search(r"(총\s*[\d,]+\s*건|[\d,]+건\s*검색됨)", html)
    if m:
        num = re.search(r"[\d,]+", m.group())
        return int(num.group().replace(",", "")) if num else None
    return None

def read_total_count(driver, wait, retries=3, sleep=0.5):
    """
    <span class="total-news-cnt">가 실제 숫자를 가질 때까지 기다리며 안전하게 파싱.
    비어 있거나 공백이면 재시도.
    """
    for i in range(retries):
        try:
            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.total-news-cnt")))
            raw = (el.get_attribute("innerText") or el.text or "").strip().replace(",", "")
            if raw.isdigit():
                return int(raw)
        except Exception as e:
            pass
        time.sleep(sleep)

    # 마지막으로 JS로 직접 읽어보기 (DOM이 보이는데 selenium text가 비는 경우)
    try:
        raw = driver.execute_script(
            "return (document.querySelector('span.total-news-cnt') || {}).textContent || '';"
        ).strip().replace(",", "")
        if raw.isdigit():
            return int(raw)
    except:
        pass

    return None



def get_total_articles_and_per_page(driver):
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.news-inner")))
    per_page = len(driver.find_elements(By.CSS_SELECTOR, "div.news-inner"))

    # 1) total-news-cnt 시도
    total = read_total_count(driver, wait)
    if total is not None:
        print(f"✅ 'total-news-cnt'에서 총 기사 수 추출 성공 → {total}건")
        return total, per_page

    # 2) header 정규식
    try:
        header = driver.find_element(By.CSS_SELECTOR, ".data-result-hd").get_attribute("innerText")
        m = re.search(r"([\d,]+)\s*건", header)
        if m:
            total = int(m.group(1).replace(",", ""))
            print(f"⚠️ header 정규식 기반 총 기사 수 추정 → {total}건")
            return total, per_page
    except Exception as e:
        print(f"⚠️ header 정규식 추출 실패: {e}")

    # 3) 페이징 숫자 기반 추정
    try:
        paging_buttons = driver.find_elements(By.CSS_SELECTOR, ".pagination a.page-link")
        nums = [int(b.text) for b in paging_buttons if b.text.isdigit()]
        last_page = max(nums) if nums else 1
        total = per_page * last_page
        print(f"⚠️ fallback: 페이지 수 기반 총 기사 수 추정 → {total}건")
    except Exception:
        total = per_page

    return total, per_page




def set_date_filter(driver, wait, method, start_date, end_date, period_label):
    driver.execute_script("document.querySelector('a.search-tab_group[title=\"Close\"]').click()")
    time.sleep(0.3)

    if method == "preset":
        if not period_label:
            raise ValueError("date_method='preset' 인 경우 period_label이 필요합니다.")
        radio = driver.find_element(By.ID, period_label)
        driver.execute_script("arguments[0].click();", radio)
        print(f"✅ preset 기간 '{period_label}' 선택 완료")
    elif method == "manual":
        if not (start_date and end_date):
            raise ValueError("date_method='manual' 인 경우 start_date, end_date가 필요합니다.")
        driver.execute_script(f"document.getElementById('search-begin-date').value = '{start_date}';")
        driver.execute_script(f"document.getElementById('search-end-date').value = '{end_date}';")
        driver.execute_script("$('#search-begin-date').trigger('change');")
        driver.execute_script("$('#search-end-date').trigger('change');")
        print(f"✅ 날짜 수동 입력: {start_date} ~ {end_date}")
    else:
        raise ValueError("date_method는 'preset' 또는 'manual'이어야 합니다.")

    time.sleep(0.5)

def click_apply(driver, wait):
    apply_btns = driver.find_elements(By.CSS_SELECTOR, "button.news-search-btn")
    for btn in apply_btns:
        if "적용" in btn.text:
            driver.execute_script("arguments[0].click();", btn)
            return
    # fallback
    apply_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.news-search-btn")))
    driver.execute_script("arguments[0].click();", apply_btn)

def extract_article_content(driver, article_el, global_index, existing_keys=None, model=None):
    """
    stale element 방지 버전.
    - 매번 fresh 요소로 다시 찾는다.
    - 팝업 열기 전 메타데이터(title/press/date 등) 먼저 뽑는다.
    - 팝업은 열고 내용만 뽑은 뒤 ESC로 닫는다.
    """
    try:
        wait = WebDriverWait(driver, 10)

        # --- 팝업 열기 전에 필요한 정보 뽑기 (DOM 변경 전에 안전하게) ---
        title = article_el.find_element(By.CSS_SELECTOR, ".title-elipsis").get_attribute("innerText").strip()

        try:
            press_el = article_el.find_element(By.CSS_SELECTOR, "a.provider")
            press = press_el.get_attribute("innerText").strip()
            link = press_el.get_attribute("href") or ""
        except Exception:
            press, link = "(언론사 없음)", ""

        date, writer = "", ""
        for el in article_el.find_elements(By.CSS_SELECTOR, "p.name"):
            txt = (el.get_attribute("innerText") or "").strip()
            if re.match(r"\d{4}/\d{2}/\d{2}", txt):
                date = txt
            elif "기자" in txt or "@" in txt:
                writer = txt

        # ✅ 여기서 중복 여부 확인 → 중복이면 팝업 열지 않고 스킵
        if existing_keys is not None and (title, date, press, link) in existing_keys:
            print(f"⏭ 중복기사 스킵(본문 미수집): [{date}] {press} | {title[:40]}...")

            # ✅ DB에서 summary 보완 시도
            summary = find_summary_any_model(title, date)
            if summary:
                print(f"🛠 DB에서 summary 보완: {title[:30]}")


            # meta만 필요하면 아래처럼 summary=None으로 반환해도 되고,
            # 아예 제외하려면 return None (분석 쪽에서 DB 재사용으로 채워짐)
            return {
                "title": title,
                "press": press,
                "date": date,
                "writer": writer,
                "summary": summary,  # 본문은 DB 재사용에 맡김
                "link": link
            }



        # --- 팝업 열기 ---
        clickable = article_el.find_element(By.CSS_SELECTOR, "a.news-detail")

        # 이전 팝업 내용
        try:
            prev_summary = driver.find_element(By.CLASS_NAME, "news-view-content").get_attribute("innerText")
        except Exception:
            prev_summary = ""

        driver.execute_script("arguments[0].click();", clickable)

        # 내용 변경 감지 (이전 내용과 다를 때까지)
        wait.until(lambda d: d.find_element(By.CLASS_NAME, "news-view-content").get_attribute("innerText") != prev_summary)

        summary = driver.execute_script(
            "return document.querySelector('.news-view-content')?.textContent?.trim();"
        )

        # --- 팝업 닫기 ---
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.2)

        print(f"[{global_index}] {date} | {press} | {title[:40]}...")
        return {
            "title": title,
            "press": press,
            "date": date,
            "writer": writer,
            "summary": summary,
            "link": link
        }

    except (TimeoutException, NoSuchElementException, StaleElementReferenceException) as e:
        # 조용히 실패 처리 (print 없애고 싶으면 주석 처리)
        print(f"⚠️ [{global_index}] 기사 추출 실패: {type(e).__name__} - {e}")
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
        return None
    except Exception as e:
        print(f"⚠️ [{global_index}] 알 수 없는 오류: {e}")
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
        return None


def extract_article_content_fast(driver, article_element):
    try:
        # ✅ 팝업 클릭 전에 newsid 가져오기 (DOM 변경되기 전에)
        news_id = article_element.get_attribute("data-id")

        # ✅ 팝업 클릭
        article_element.find_element(By.CSS_SELECTOR, "a.news-detail").click()

        # ✅ 팝업 내용 기다리고 가져오기
        content_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".news-view-content"))
        )
        content = content_elem.text.strip()

        # ✅ 팝업 닫기 (ESC로 빠르게)
        driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.2)

        return content

    except StaleElementReferenceException:
        print(f"⚠️ [Stale] 기사 재시도: {news_id}")
        return None  # 또는 retry 로직
    except Exception as e:
        print(f"⚠️ 기사 추출 실패: {e}")
        return None


def prepare_search(driver, config):
    """
    각 프로세스에서 공통적으로: 페이지 접속 → 필터/키워드 설정 → 적용
    """
    wait = WebDriverWait(driver, 10)

    driver.get("https://www.bigkinds.or.kr/v2/news/index.do")
    time.sleep(1)

    # 통합분류
    if config["unified_category"]:
        driver.find_element(By.CSS_SELECTOR, "a.tab3.search-tab_group").click()
        time.sleep(0.3)
        for cat in config["unified_category"]:
            try:
                box = wait.until(EC.presence_of_element_located((
                    By.XPATH, f"//span[normalize-space(text())='{cat}']/preceding::input[@type='checkbox'][1]"
                )))
                if not box.is_selected():
                    driver.execute_script("arguments[0].click();", box)
            except Exception as e:
                print(f"❌ 통합분류 '{cat}' 선택 실패: {e}")

    # 사건사고분류
    if config["incident_category"]:
        driver.find_element(By.CSS_SELECTOR, "a.tab4.search-tab_group").click()
        time.sleep(0.3)
        for cat in config["incident_category"]:
            try:
                box = wait.until(EC.presence_of_element_located((
                    By.XPATH, f"//span[normalize-space(text())='{cat}']/preceding::input[@type='checkbox'][1]"
                )))
                if not box.is_selected():
                    driver.execute_script("arguments[0].click();", box)
            except Exception as e:
                print(f"❌ 사건사고분류 '{cat}' 선택 실패: {e}")

    # 날짜
    set_date_filter(
        driver,
        wait,
        method=config["date_method"],
        start_date=config["start_date"],
        end_date=config["end_date"],
        period_label=config["period_label"]
    )

    # 키워드
    search_input = wait.until(EC.presence_of_element_located((By.ID, "total-search-key")))
    search_input.clear()
    search_input.send_keys(config["keyword"])

    click_apply(driver, wait)
    time.sleep(1)

def get_current_page(driver, retries=2, sleep=0.2):
    for _ in range(retries + 1):
        try:
            page_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input#paging_news_result"))
            )
            return int((page_input.get_attribute("value") or "1").strip())
        except Exception:
            time.sleep(sleep)
            continue
    # print 안 하고 기본값만 반환
    return 1



def goto_page(driver, target_page: int, wait=None, logger_prefix=""):
    if wait is None:
        wait = WebDriverWait(driver, 10)

    def cur():
        p = get_current_page(driver)
        return p if p else 1

    current_page = cur()
    if current_page == target_page:
        return True

    # 같은 pagination block 안이면 해당 번호 클릭
    try:
        btn = driver.find_elements(By.CSS_SELECTOR, f".pagination a.page-link[data-page='{target_page}']")
        for b in btn:
            txt = (b.text or "").strip()
            if txt.isdigit() and int(txt) == target_page:
                driver.execute_script("arguments[0].click();", b)
                WebDriverWait(driver, 10).until(lambda d: cur() == target_page)
                print(f"{logger_prefix}📍 번호 클릭으로 {target_page} 이동 성공")
                return True
    except Exception:
        pass

    # 번호가 안 보이면 next-block 반복
    max_jump = 30
    for _ in range(max_jump):
        current_page = cur()
        if current_page == target_page:
            return True

        # 현재 페이지 블록에서 마지막 번호 찾기
        nums = []
        for a in driver.find_elements(By.CSS_SELECTOR, ".pagination a.page-link"):
            t = (a.text or "").strip()
            if t.isdigit():
                nums.append(int(t))
        last_in_block = max(nums) if nums else current_page

        if target_page <= last_in_block:
            # target이 보이는 블록인데 위에서 클릭 실패했음 -> 다시 시도
            try:
                btn = driver.find_element(By.CSS_SELECTOR, f".pagination a.page-link[data-page='{target_page}']")
                driver.execute_script("arguments[0].click();", btn)
                WebDriverWait(driver, 10).until(lambda d: cur() == target_page)
                return True
            except Exception as e:
                print(f"{logger_prefix}⚠️ target 버튼 클릭 실패: {e}")
                return cur() == target_page

        # 다음 블록으로
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "a.page-next.page-link:not(.disabled)")
            driver.execute_script("arguments[0].click();", next_btn)
            WebDriverWait(driver, 10).until(lambda d: cur() != current_page)
        except Exception as e:
            print(f"{logger_prefix}❌ 다음 블록으로 이동 실패: {e}")
            return False

    return cur() == target_page



MAX_RETRY = 4  # 필요시 조절


def crawl_page_range(proc_id, page_range, config, per_page, existing_keys=None):
    """
    각 프로세스에서 담당 페이지 범위를 크롤링
    - page_range: (start_page, end_page)
    """
    start_page, end_page = page_range
    driver = None
    results = []

    try:
        driver = undetected_driver(headless=True)
        apply_speed_up(driver)
        prepare_search(driver, config)

        wait = WebDriverWait(driver, 10)

        # 시작 페이지로 이동
        if start_page > 1:
            ok = goto_page(driver, start_page)
            if not ok:
                print(f"[P{proc_id}] ❌ {start_page} 페이지로 이동 실패")
                return results

        global_index = (start_page - 1) * per_page  # 진행 표시용 index offset

        MAX_RETRY = 2  # 필요시 조절

        for page in range(start_page, end_page + 1):
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.news-inner")))

                # ✅ 이 줄이 핵심: 실제 길이(len)를 기준으로 돔을 매번 새로 읽어온다
                fresh_elements = driver.find_elements(By.CSS_SELECTOR, "div.news-inner")

                for idx in range(len(fresh_elements)):
                    attempt = 0
                    while attempt <= MAX_RETRY:
                        try:
                            # **여기서도 fresh하게 다시 뽑아온다**
                            fresh_elements = driver.find_elements(By.CSS_SELECTOR, "div.news-inner")

                            if idx >= len(fresh_elements):
                                break
                            el = fresh_elements[idx]

                            # ✅ 기존: extract_article_content(driver, el, global_index + idx + 1)
                            item = extract_article_content(
                                driver, el, global_index + idx + 1,
                                existing_keys=existing_keys,
                                model=config.get("model")  # config에 model 추가 필요
                            )

                            if item:
                                    results.append(item)
                            break  # 성공했으면 retry loop 탈출
                        except StaleElementReferenceException as e:
                            attempt += 1
                            if attempt > MAX_RETRY:
                                print(f"[{global_index + idx + 1}] Stale 재시도 초과 → 스킵")
                            else:
                                time.sleep(0.15)  # 살짝 대기 후 재시도
                        except Exception as e:
                            print(f"[{global_index + idx + 1}] 기사 추출 실패: {e}")
                            break

                # 마지막 페이지면 종료
                if page == end_page:
                    break

                # 다음 페이지
                next_btn = driver.find_element(By.CSS_SELECTOR, "a.page-next")
                cls = next_btn.get_attribute("class") or ""
                if "disabled" in cls:
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(0.2)
                global_index += per_page

            except Exception as e:
                print(f"[P{proc_id}] ⚠️ {page}페이지 처리 중 오류: {e}")
                break

        print(f"[P{proc_id}] ✅ 완료: {start_page}~{end_page}페이지, 수집 {len(results)}건")
        return results

    except Exception as e:
        print(f"[P{proc_id}] ❌ 치명적 오류: {e}")
        return results
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def deduplicate(items):
    seen = set()
    out = []
    for it in items:
        title = it.get("title") or ""
        date = it.get("date") or ""
        key = f"{title}|{date}"
        if key not in seen:
            out.append(it)
            seen.add(key)
    return out

def count_duplicates(items, key_fn=lambda x: (x.get("title", ""), x.get("date", ""))):
    """중복 기사 개수와 어떤 키가 중복됐는지를 반환"""
    keys = [key_fn(it) for it in items]
    c = Counter(keys)
    dup_map = {k: v for k, v in c.items() if v > 1}
    total_dups = sum(v - 1 for v in dup_map.values())
    return total_dups, dup_map

def auto_parallel_crawl(config):
    # config에서 model 없으면 기본값으로 vote 설정
    if "model" not in config:
        config["model"] = "vote"

    """
    1) 한 번만 드라이버를 띄워 총 기사 수와 per_page 추출
    2) 페이지 수와 CPU 코어 수로 병렬 분할
    3) Pool로 병렬 크롤
    4) 결과 병합/중복 제거/저장
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SAVE_DIR = os.path.join(BASE_DIR, "newsCrawlingData")
    os.makedirs(SAVE_DIR, exist_ok=True)

    safe_keyword = re.sub(r'[\\/*?:"<>|]', "_", config["keyword"])
    year = config.get("year") or datetime.today().strftime("%Y")
    result_filename = os.path.join(SAVE_DIR, f"{year}_{safe_keyword}_article.json")


    # 1) 사전 분석
    driver = undetected_driver(headless=True)
    apply_speed_up(driver)


    # ✅ 크롤 시작 전에 DB에 저장된 메타 키셋을 한 번 로딩
    try:
        existing_keys = get_existing_keys()
        print(f"🗂 기존 저장 기사 키 개수: {len(existing_keys)}")
    except Exception as e:
        print(f"⚠️ 기존 키 로딩 실패(스킵): {e}")
        existing_keys = None

    try:
        prepare_search(driver, config)
        total, per_page = get_total_articles_and_per_page(driver)

        # ✅ max_articles가 지정되면 총 건수를 그 이하로 제한
        if config.get("max_articles"):
            total = min(total, config["max_articles"])

        total_pages = max(1, math.ceil(total / per_page))
        print(f"📊 총 {total:,}건 / 페이지당 {per_page}건 / 총 {total_pages}페이지")

        # 2) 프로세스 개수 결정
        phys_cores = cpu_count()  # 논리 코어 수. (psutil 없이 간단)
        # 물리 코어 6, 논리 12 환경 -> 4개 추천
        default_proc = 4 if phys_cores >= 8 else 2
        processes = min(default_proc, total_pages)
        if processes < 1:
            processes = 1
        print(f"🧵 병렬 프로세스 수: {processes}")

        # 3) 페이지 범위 분할
        # 예) total_pages=13, processes=4 -> (1~4), (5~8), (9~12), (13~13)
        # 3) 페이지 범위 분할
        pages_per_proc = math.ceil(total_pages / processes)
        page_ranges = []
        start = 1
        for p in range(processes):
            if start > total_pages:  # ✅ 여기에 조건 추가
                break
            end = min(total_pages, start + pages_per_proc - 1)
            page_ranges.append((start, end))
            start = end + 1

        print(f"🗂 분할 페이지 범위: {page_ranges}")

        # 4) 병렬 실행
        args = []
        for i, pr in enumerate(page_ranges, start=1):
            args.append((i, pr, config, per_page, existing_keys))

        t0 = time.time()
        with Pool(processes=processes) as pool:
            parts = pool.starmap(crawl_page_range, args)
        elapsed = time.time() - t0

        # 5) 결과 병합 (dedupe 전에 원본 유지)
        merged_raw = []
        for part in parts:
            merged_raw.extend(part)

        # 🔍 중복 개수 계산 (dedupe 이전)
        total_dups, dup_map = count_duplicates(
            merged_raw,
            key_fn=lambda x: (x.get("title", ""), x.get("date", ""))  # 필요 시 press도 포함
            # key_fn=lambda x: (x.get("title", ""), x.get("date", ""), x.get("press", ""))
        )
        print(f"\n🔍 중복 키 개수: {len(dup_map)}")
        print(f"📉 총 중복 기사 수: {total_dups}")
        print(f"🧾 dedupe 전 원본 수집: {len(merged_raw)}건")

        # (선택) 어떤 키가 얼마나 중복됐는지 보고 싶으면:
        # for k, v in dup_map.items():
        #     print(f"- {k} → {v}회 수집")

        # 6) dedupe
        merged = deduplicate(merged_raw)
        print(f"✅ dedupe 이후: {len(merged)}건")

        # ✅ 날짜 + 제목 기준 정렬 추가
        # merged = sorted(merged, key=lambda x: (x.get("date", ""), x.get("title", "")))

        # ✅ 7) max_articles 개수 제한 적용
        if config.get("max_articles"):
            merged = merged[:config["max_articles"]]
            print(f"🔢 최종 반환 수 (max_articles 적용): {len(merged)}건")

        return merged

    finally:
        try:
            driver.quit()
        except:
            pass

def search_bigkinds(
    keyword,
    unified_category=None,
    incident_category=None,
    start_date=None,
    end_date=None,
    date_method="preset",
    period_label=None,
    max_articles=None
):
    config = {
        "keyword": keyword,
        "unified_category": unified_category or [],
        "incident_category": incident_category or [],
        "start_date": start_date,
        "end_date": end_date,
        "date_method": date_method,
        "period_label": period_label,
        "year": start_date[:4] if start_date else time.strftime("%Y"),
        "max_articles": max_articles,
    }
    return auto_parallel_crawl(config)



# ---------------------------
# 실행부
# ---------------------------
if __name__ == "__main__":
    freeze_support()  # 윈도우 멀티프로세싱 필수

    CONFIG = {
        "keyword": "하이브",
        "unified_category": ["사회", "국제", "IT_과학"],  # 또는 None / [] 가능
        "incident_category": None,                       # 또는 ["범죄", ...]
        "date_method": "preset",                         # "preset" | "manual"
        "period_label": "date1-2",                       # preset일 때만 (예: 1주)
        "start_date": None,                              # manual일 때만
        "end_date": None,                                # manual일 때만
        "year": "2025",
        "max_articles": None
    }

    start_time = time.time()
    try:
        data = auto_parallel_crawl(CONFIG)
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        data = []
    finally:
        print(f"\n⏱ 총 소요: {time.time() - start_time:.2f}초 / 수집: {len(data)}건")
