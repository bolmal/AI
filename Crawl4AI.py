import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.async_configs import CrawlerRunConfig
from bs4 import BeautifulSoup  # HTML 파싱용 라이브러리
from urllib.parse import urljoin  # 절대 경로 변환을 위한 라이브러리
import os

from markdown_it.rules_core.normalize import NULL_RE
from openai import OpenAI
from typing import List, Dict
import time
import json
from datetime import datetime
from random import uniform
import requests
import math

from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.proxy import ProxyType
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
API_URL = "https://dev.bolmal.shop/save"

# 셀레니움 드라이버 설정
options = Options()
options.page_load_strategy = 'normal'
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)


class ConcertParser:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        # 시스템 메시지는 파싱 규칙과 출력 포맷에 집중
        self.system_message = """You are a Korean concert information parser.
        Your task is to extract structured data from concert information text.
        Always output valid JSON in Korean following this exact format:
        {
            "concert_name": string,        // 공연명
            "concert_poster:" string | null,  // 포스터      
            "genre": string,              // 장르 (하나만 선택)
            "concert_mood": string,       // 공연 분위기 (하나만 선택)
            "concert_style": string,      // 공연 스타일 (하나만 선택)
            "concert_type": string,       // 공연 유형 (하나만 선택)
            "casting": [                   // 캐스팅
                {
                    "name": string
                }
            ]                  
            "performance_rounds": [        // 공연 회차 정보
                {
                    "round": number,
                    "datetime": "YYYY-MM-DDTHH:MM:SS"
                }
            ],
            "venue": string | null,        // 공연장소
            "running_time": number | null, // 러닝타임(분)
            "price": {                     // 가격 정보
                "type": number             // 좌석 유형별 가격
            },
            "age_limit": string | null,    // 관람연령
            "booking_limit": string | null, // 예매제한
            "selling_platform": "INTERPARK",  // 판매처
            "ticket_status": boolen,       // 티켓 오픈 여부
            "ticket_open_dates": {       // 티켓 오픈 일정
                    "round": YYYY-MM-DDTHH:MM:SS
                }
            "booking_link": string | null,  // 예매 링크
            "additional_info": "이것은 하나의 문자열입니다."  // 추가정보
        }"""

    def parse_single_concert(self, concert_text: str) -> dict:
        """단일 공연 정보 파싱"""
        prompt = f"""다음 공연 정보를 파싱하여 JSON 형식으로 변환하세요.

        규칙:
        1. 날짜와 시간은 모두 YYYY-MM-DDTHH:MM:SS 형식을 사용
        2. 가격은 숫자로 변환 (예: "90,000원" → 90000)
        3. 정보가 없는 경우 null 사용
        4. ticket_status는 True 또는 False 중 하나로 표시
        5. ticket_open_dates는 다음 형식을 반드시 따를 것:
           - key는 예매 유형 또는 회차 번호
           - value는 YYYY-MM-DDTHH:MM:SS 형식의 날짜
        6. 다음 필드들은 각각 정해진 값 중 하나만 선택해야 합니다:
            genre는 다음 중 하나만 선택:
            ["발라드","댄스","랩/힙합","아이돌","R&B/Soul","인디음악","록/메탈","성인가요/트로트",
            "포크/블루스","일렉트로니카","클래식","재즈","J-POP","POP","키즈","CCM","국악"]
       
            concert_mood는 다음 중 하나만 선택:
            ["Emotional","Energetic","Dreamy","Grand","Calm","Fun","Intense"]
       
            concert_style는 다음 중 하나만 선택:
            ["Live Band","Acoustic","Orchestra","Solo Performance","Dance Performance","Theatrical Concert"]
       
            concert_type는 다음 중 하나만 선택:
            ["Festival","Concert","Music Show","Fan Meeting","Talk Concert"]
        
        공연 정보:
        {concert_text}
        """

        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1  # 일관된 출력을 위해 낮은 temperature 사용
            )

            # JSON 파싱 검증
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error parsing concert data: {e}")
            return None

    def parse_multiple_concerts(self, crawled_concerts: List[str]) -> List[Dict]:
        """여러 공연 정보를 배치로 처리"""
        results = []
        for idx, concert_text in enumerate(crawled_concerts):
            try:
                # API 레이트 리밋 고려
                if idx > 0:
                    time.sleep(0.5)

                print(f"Parsing concert {idx + 1}/{len(crawled_concerts)}")
                result = self.parse_single_concert(concert_text)

                if result:
                    results.append(result)
                    print(f"Successfully parsed concert {idx + 1}")
                else:
                    print(f"Failed to parse concert {idx + 1}")

            except Exception as e:
                print(f"Error processing concert {idx + 1}: {e}")
                continue

        return results

"""재시도 로직이 포함된 크롤링 함수"""
async def crawl_with_retry(max_retries: int = 1):
    min_num_of_error = 100
    final_crawled_concert = False
    parsed_results = False
    for attempt in range(1,max_retries+1):
        try:
            # 랜덤 대기 시간 추가
            await asyncio.sleep(uniform(3, 5))

            # 크롤링 시도
            crawrled_data, num_of_error = await crawl_and_parse_concerts(page_num=attempt)
            print("에러수 :",num_of_error)
            if parsed_results:
                parsed_results.append(crawrled_data)
            else:
                parsed_results=crawrled_data
            # if num_of_error < min_num_of_error:
            #     min_num_of_error = num_of_error
            #     final_crawled_concert = crawrled_data

            #     if parsed_results:
            #         # GPT 파싱 처리
            #         parser = ConcertParser()
            #         parsed_results.append(parser.parse_multiple_concerts(final_crawled_concert))
            #         print(parsed_results)
            #     else:
            #         # GPT 파싱 처리
            #         parser = ConcertParser()
            #         parsed_results=parser.parse_multiple_concerts(final_crawled_concert)
            #         print(parsed_results)

            # else:
            #     print("크롤링 문제")

        except Exception as e:
            print(f"Attempt {attempt + 1} failed for crawling",e)

        await asyncio.sleep(5)  # 재시도 전 대기

    return parsed_results

    # if final_crawled_concert:
    #     # GPT 파싱 처리
    #     parser = ConcertParser()
    #     parsed_results = parser.parse_multiple_concerts(final_crawled_concert)
    #     print(parsed_results)
    #     return parsed_results
    # else:
    #     print("크롤링 문제")


async def crawl_and_parse_concerts(page_num: int = 0):
    crawled_concerts = []
    errer_crawled_concerts = 0

    # 메인 페이지(장르 : 콘서트) 크롤링
    url = "https://tickets.interpark.com/contents/notice?Genre=CONCERT"
    # URL 접속
    driver.get(url)
    # 암시적 대기
    driver.implicitly_wait(5)

    processed_count = 0
    scroll_amount = 900  # 임의의 스크롤 거리 (px)

    MAX_ITEMS = 15  # 원하는 최대 아이템 수 제한 (예: 100개까지)
    index = 0
    items = driver.find_elements(By.CSS_SELECTOR, "a.TicketItem_ticketItem__")
    print("아이템수",len(items))

    concert_info = {}
    while  processed_count < MAX_ITEMS:

        for i in range(5):
            # 매번 fresh하게 재선언!
            items = driver.find_elements(By.CSS_SELECTOR, "a.TicketItem_ticketItem__")
            print(f"{processed_count}번째 아이템 수: ",len(items))
            print(f"현재 인덱스 : {index}")
            MAX_ITEMS = max(len(items), MAX_ITEMS)
            if(index>=len(items)):
                index-=5
                MAX_ITEMS+=5
            
            item = items[index]
            label = item.get_attribute("gtm-label")

            # 이미지 링크
            try:
                img = item.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
            except:
                img = None

            # 텍스트 정보
            try:
                texts = item.find_elements(By.CSS_SELECTOR, "ul.NoticeItem_contentsWrap__y1tdg li")
                for j, t in enumerate(texts):
                    print(f"text{j+1}:", t.text)
            except:
                pass

            print("Image:", img)

            # 상세 페이지로 이동
            href = item.get_attribute("href")
            if href:
                print("Link (a 태그 직접):", href)
            else:
                try:
                    item.click()
                    print("클릭후")

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article.DetailSummary_infoBox__5we4P"))
                    )

                    current_url = driver.current_url
                    concert_info["booking_link"] = current_url
                    print(f"[{processed_count}] 링크 수집 완료:", current_url)

                    driver.back()

                    # 다시 목록 페이지 로딩 대기
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.TicketItem_ticketItem__"))
                    )

                except Exception as e:
                    print(f"[{i+1}] 클릭 실패:", e)

            print("-" * 50)
            # 크롤링된 모든 정보를 하나의 문자열로 변환
            concert_text = f"""
            공연명: {label}
            공연 포스터: {img}
            예매링크: {current_url}
            공연정보: {texts}
            """
            print(concert_text)
            crawled_concerts.append(concert_text)
            index+=1
            processed_count +=1

    return crawled_concerts, errer_crawled_concerts

    #     # iframe 내부 URL 크롤링
    #     result = await crawler.arun(
    #         url=url,
    #         headers=headers,
    #         css_selector="td.subject",  # 필요한 데이터 선택
    #         # process_iframes=False,
    #         config=config
    #     )
    #     print("actural URL : ",result.url)
        
    #     # BeautifulSoup으로 데이터 파싱
    #     iframe_soup = BeautifulSoup(result.html, "html.parser")
    #     rows = iframe_soup.select_one("div.InfiniteList_ticket-list__dfe68")
    #     # 결과 처리
    #     for row in rows:
    #         print("row:",row)
    #         await asyncio.sleep(1)
    #         #  각 공연 정보를 저장할 딕셔너리
    #         concert_info = {}

    #         # <td class="subject">와 <a> 태그 처리
    #         subject_tag = row.select_one("td.subject a")
    #         # 장르 가져오기
    #         type_tag = row.select_one("td.type")

    #         # 이 부분에 원하는 타입의 장르만 가져 올 수 있다
    #         if type_tag and type_tag.text:
    #             concert_info['genre'] = type_tag.text.strip()
    #         else:
    #             continue

    #         if not concert_info.get('genre','') in ['콘서트','HOT']:
    #             continue

    #         if subject_tag:
    #             concert_info['title'] = subject_tag.get_text(strip=True)
    #             link = subject_tag.get("href")
    #             absolute_link = urljoin(url, link)
    #             print("링크:",absolute_link)
    #             concert_info['link'] = absolute_link

    #             # new <img> 태그 확인 (새로 뜬 공지)
    #             new_img_tag = row.select_one("td.subject img.ico_new")
    #             concert_info['is_new'] = bool(new_img_tag)

    #             print("new img tag :",new_img_tag)

    #             if absolute_link:
    #                 await asyncio.sleep(3)  # 상세링크 크롤링 전 대기

    #                 async with AsyncWebCrawler(verbose=True) as crawler_concert:
    #                     # 메인 페이지 크롤링
    #                     result_concert = await crawler_concert.arun(url=absolute_link,config=config)

    #                     if not result_concert.success:
    #                         print(f"Crawl failed: {result_concert.error_message}")
    #                         print(f"Status code: {result_concert.status_code}")
    #                         errer_crawled_concerts += 1

    #                 # BeautifulSoup 객체 생성
    #                 soup_concert = BeautifulSoup(result_concert.html, 'html.parser')

    #                 # 포스터 사진
    #                 poster_div = soup_concert.select_one("div.DetailSummary_imageContainer__OmWus")
    #                 if poster_div:
    #                     poster_tag = poster_div.find("img")  # <img> 태그 찾기
    #                     if poster_tag :
    #                         img_url = poster_tag.get("src")
    #                         # 프로토콜이 없는 경우 http: 추가
    #                         if img_url.startswith("//"):
    #                             img_url = "https:" + img_url
    #                         concert_info['poster'] = img_url
    #                 else:
    #                     errer_crawled_concerts += 1
    #                     if poster_div and poster_div.text:
    #                         concert_info['info'] = poster_div.text.strip()

    #                 # 공연 요약 정보
    #                 concert_summary_div = soup_concert.select_one("article.DetailSummary_infoBox__5we4P")
    #                 if concert_summary_div and concert_summary_div.text:
    #                     concert_info['summary'] = concert_summary_div.text.strip()
    #                 else:
    #                     print("concert_summary_div 없음 또는 내용 없음:", concert_summary_div)
    #                     concert_info['summary'] = None
                    
    #                 # 공연 디테일 정보
    #                 concert_detail_div = soup_concert.select_one(".DetailInfo_contents__grsx5.DetailInfo_isOld__4UynI")
    #                 if concert_detail_div and concert_detail_div.text:
    #                     concert_info['description'] = concert_detail_div.text.strip()
    #                 else:
    #                     print("concert_detail_div 없음 또는 내용 없음:", concert_detail_div)
    #                     concert_info['description'] = None
                        
    #                 # <a class="btn_book"> 태그 처리 예약 버튼
    #                 book_button_tag = soup_concert.select_one("button.DetailBooking_bookingBtn__uvSid")
    #                 if book_button_tag:
    #                     concert_info['booking_link'] = absolute_link
    #                     concert_info['ticket_status'] = "True"
    #                 else :
    #                     concert_info['ticket_status'] = "False"

    #                 # 크롤링된 모든 정보를 하나의 문자열로 변환
    #                 concert_text = f"""
    #                 공연명: {concert_info.get('title', '')}
    #                 공연 포스터: {concert_info.get('poster', '')}
    #                 장르: {concert_info.get('genre', '')}
    #                 티켓상태: {concert_info.get('ticket_status', '')}
    #                 공연정보: {concert_info.get('info', '')}
    #                 공연요약: {concert_info.get('summary', '')}
    #                 공연설명: {concert_info.get('description', '')}
    #                 예매링크: {concert_info.get('booking_link', '티켓 미오픈')}
    #                 """
    #                 print(concert_text)
    #                 crawled_concerts.append(concert_text)

    # return crawled_concerts, errer_crawled_concerts

# 실행 코드
async def main():
    # 크롤링 코드 실행
    results = await crawl_with_retry()

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

