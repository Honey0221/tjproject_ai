# pip install selenium
# pip install -U user_agent
# pip install user-agents
# pip install webdriver_manager

from user_agent import generate_user_agent
from user_agents import parse
from selenium import webdriver  # 자동화 툴
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import warnings

warnings.filterwarnings('ignore')

# ✅ 기존 함수 (원본 유지)
def chrome_driver():
    userAgent = generate_user_agent()
    user_agent = parse(userAgent)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("disable-infobars")
    chrome_options.page_load_strategy = 'normal'
    chrome_options.add_argument('--enable-automation')
    chrome_options.add_argument('disable-infobars')
    chrome_options.add_argument('disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('user-agent={}'.format(user_agent))
    chrome_options.add_argument('--lang=ko_KR')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--allow-insecure-localhost')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-browser-side-navigation')
    chrome_options.add_argument('--mute-audio')
    # chrome_options.add_argument('--headless')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=chrome_options)
    driver.implicitly_wait(3)
    return driver


# ✅ BigKinds 우회용 드라이버 (추가된 함수)
def undetected_driver(headless=False):
    userAgent = generate_user_agent()

    chrome_options = webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless=new")

    # 우회 관련 설정
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={userAgent}")
    chrome_options.add_argument('--lang=ko_KR')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--mute-audio')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # ✅ 로그 숨기기
    chrome_options.add_argument("--log-level=3")  # fatal only

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    # navigator.webdriver = undefined 처리
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
        """
    })

    driver.implicitly_wait(3)
    return driver


# ✅ 테스트용 실행 (직접 실행 시만 사용)
if __name__ == "__main__":
    driver = chrome_driver()
