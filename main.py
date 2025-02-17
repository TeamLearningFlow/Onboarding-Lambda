import os
import json
import boto3
import hashlib
import time
from selenium import webdriver
from tempfile import mkdtemp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# ✅ 환경 변수 설정 (한글 폰트 적용)
os.environ["LANG"] = "ko_KR.UTF-8"
os.environ["FONTCONFIG_PATH"] = "/etc/fonts"

def get_driver(url, width, height):
    """블로그 유형별로 Chrome WebDriver 옵션을 설정"""
    options = webdriver.ChromeOptions()
    service = webdriver.ChromeService("/opt/chromedriver")

    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--enable-software-compositing")
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")

    # ✅ 벨로그와 티스토리에는 한글 폰트 적용
    if "tistory.com" in url or "velog.io" in url:
        options.add_argument("--font-render-hinting=medium")  # 폰트 힌팅 조정
        options.add_argument("--enable-font-antialiasing")  # 폰트 안티앨리어싱 활성화
        options.add_argument("--lang=ko-KR")  # 한글 렌더링 지원
        options.add_argument("--force-color-profile=srgb")  # 색상 프로필 고정
        options.add_argument("--disable-blink-features=AutomationControlled")  # 자동화 탐지 방지

    driver = webdriver.Chrome(options=options, service=service)
    return driver


def process_naver_blog(driver):
    """네이버 블로그 전용 크롤링 처리 (폰트 변경 금지)"""
    try:
        driver.switch_to.frame(driver.find_element(By.TAG_NAME, "iframe"))
        time.sleep(2)  # iframe 로딩 대기
        total_height = driver.execute_script("return document.body.scrollHeight")
    except Exception as e:
        print(f"❌ 네이버 블로그 iframe 접근 실패: {e}")
        total_height = driver.execute_script("return document.body.scrollHeight")
    
    return total_height


def process_tistory_blog(driver, height):
    """티스토리 블로그 전용 크롤링 처리 (폰트 적용)"""
    scroll_pause_time = 0.5
    current_scroll = 0
    scroll_increment = height
    total_height = driver.execute_script("return document.body.scrollHeight")

    while current_scroll < total_height:
        driver.execute_script(f"window.scrollTo(0, {current_scroll});")
        time.sleep(scroll_pause_time)
        current_scroll += scroll_increment
        total_height = driver.execute_script("return document.body.scrollHeight")
    
    return total_height


def process_velog_blog(driver, height):
    """벨로그 블로그 전용 크롤링 처리 (폰트 적용)"""
    return process_tistory_blog(driver, height)  # 벨로그도 티스토리와 동일한 방식

def ensure_scroll_top(driver):
    """스크롤이 최상단으로 이동할 때까지 기다림"""
    driver.execute_script("window.scrollTo(0, 0);")
    WebDriverWait(driver, 3).until(lambda d: d.execute_script("return window.scrollY;") == 0)


def capture_screenshot(url, width, height):
    """Selenium을 이용하여 블로그 스크린샷 촬영"""
    driver = get_driver(url, width, height)
    driver.get(url)
    time.sleep(3)

    total_height = driver.execute_script("return document.body.scrollHeight")

    # 블로그별 맞춤 크롤링 적용
    if "blog.naver.com" in url:
        total_height = process_naver_blog(driver)
    elif "tistory.com" in url:
        total_height = process_tistory_blog(driver, height)
    elif "velog.io" in url:
        total_height = process_velog_blog(driver, height)

    # 전체 페이지 캡처
    driver.set_window_size(width, total_height)
    time.sleep(1)
    ensure_scroll_top(driver)

    screenshot = driver.get_screenshot_as_png()
    driver.quit()

    return screenshot


def handler(event, context):
    url = event.get("url", None)
    width = event.get("width", 982)
    height = event.get("height", 552)
    
    if not url:
        return {"statusCode": 400, "body": json.dumps({"error": "No URL provided"})}

    screenshot = capture_screenshot(url, width, height)

    file_name = hashlib.md5(url.encode()).hexdigest() + ".png"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f"blog_screenshots/{file_name}",
        Body=screenshot,
        ContentType="image/png"
    )

    s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/blog_screenshots/{file_name}"

    return {
        "statusCode": 200,
        "body": json.dumps({"s3_url": s3_url})
    }
