import asyncio
import os
import time
import json
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from parseDetail import parseDetail
from makeJson import makeJson, ConcertParser


OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
API_URL = "https://dev.bolmal.shop/save"

# 셀레니움 드라이버 설정
options = Options()
options.page_load_strategy = 'normal'
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)

async def crawlConcerts() -> list[str]:
    crawledConcerts = []
    errerCrawledConcerts = 0

    # 메인 페이지(장르 : 콘서트) 크롤링
    url = "https://tickets.interpark.com/contents/notice?Genre=CONCERT"
    # URL 접속
    driver.get(url)
    # 암시적 대기
    driver.implicitly_wait(5)

    SCROLL_AMOUNT = 700
    SCROLL_WAIT = 1.5
    MAX_SCROLL_END_RETRY = 3

    seenLabels = set()
    crawledConcerts = []

    scrollEndCounter = 0
    prevSeenCount = 0

    while True:
        items = driver.find_elements(By.CSS_SELECTOR, "a.TicketItem_ticketItem__")
        print(f"현재 화면 공연 수: {len(items)}")

        newLabels = []
        for item in items:
            try:
                label = item.get_attribute("gtm-label")
                if label and label not in seenLabels:
                    newLabels.append(label)
                    seenLabels.add(label)
            except:
                continue

        for label in newLabels:
            try:                
                # 텍스트 정보
                try:
                    texts = item.find_elements(By.CSS_SELECTOR, "ul.NoticeItem_contentsWrap__y1tdg li")
                    infoList = [t.text.strip() for t in texts]
                    infoStr = ", ".join(infoList)
                    print(f"공연정보: {infoStr}")
                except:
                    pass

                # 상세 링크
                # 매번 fresh하게 클릭할 요소 다시 찾기
                clickable = driver.find_element(By.CSS_SELECTOR, f"a[gtm-label='{label}']")
                clickable.click()

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article.DetailSummary_infoBox__5we4P"))
                )

                currentUrl = driver.current_url
                print(f"🎟️ [{label}] 상세 링크:", currentUrl)

                concertText = f"""
                    공연명: {label}
                    공연 정보: {infoStr}
                    예매링크: {currentUrl}
                    """
                crawledConcerts.append(concertText)
                print(concertText)

                driver.back()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.TicketItem_ticketItem__"))
                )
            except Exception as e:
                print(f"⚠️ a[gtm-label='{label}'] -- 처리 중 에러:", e)
                continue

        # 스크롤 종료 감지
        if len(seenLabels) == prevSeenCount:
            scrollEndCounter += 1
            if scrollEndCounter >= MAX_SCROLL_END_RETRY:
                print("✅ 더 이상 새로운 항목 없음. 종료.")
                break
        else:
            scrollEndCounter = 0
            prevSeenCount = len(seenLabels)

        driver.execute_script(f"window.scrollBy(0, {SCROLL_AMOUNT});")
        time.sleep(SCROLL_WAIT)


    return crawledConcerts, errerCrawledConcerts

async def crawlConcert() -> list[str]:
    # 오픈예정 공연 크롤링
    crawrledData, numOfError = await crawlConcerts()
    print("에러수 :",numOfError)

    # 공연 상세 크롤링
    finalOutput = parseDetail(crawrledData)

    # json 형식으로 저장
    # result = makeJson(finalOutput,api_key=OPENAI_API_KEY)
    result = ConcertParser.make_json_with_langchain(finalOutput,OPENAI_API_KEY)
    return result

# 실행 코드
async def main():
    # 크롤링 코드 실행
    results = await crawlConcert()

    # 결과 제출
    current_dir = os.getcwd()
    target_dir = os.path.join(current_dir, 'crawl_new_concerts')
    os.makedirs(target_dir, exist_ok=True)

    # 현재 날짜를 파일 이름으로 저장
    current_date = datetime.now().strftime('%Y-%m-%d')  # 'YYYY-MM-DD' 형식
    file_path = os.path.join(target_dir, f'{current_date}.json')

    # JSON 파일로 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # HTTP 헤더 설정 (JSON 형식)
    headers = {"Content-Type": "application/json"}

    # # JSON 파일 열기 및 데이터 로드
    # with open(f'crawl_new_concerts/{file_path}', 'r', encoding='utf-8') as f:
    #     data_list = json.load(f)  # 이제 data_list는 Python 리스트입니다

    # response = requests.post(API_URL, headers=headers, json=data_list)  # `json=data` 사용

    # 응답 확인
    # print("응답 코드:", response.status_code)

if __name__ == "__main__":
    asyncio.run(main())

