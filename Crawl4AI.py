import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.async_configs import CrawlerRunConfig
from bs4 import BeautifulSoup  # HTML 파싱용 라이브러리
from urllib.parse import urljoin  # 절대 경로 변환을 위한 라이브러리
import os
from openai import OpenAI
from typing import List, Dict
import time
import json
from datetime import datetime
import requests

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
API_URL = "http://dev.bolmal.shop/concerts/save"

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
            "additional_info": {           // 추가 정보
            }
        }"""

    def parse_single_concert(self, concert_text: str) -> dict:
        """단일 공연 정보 파싱"""
        prompt = f"""다음 공연 정보를 파싱하여 JSON 형식으로 변환하세요.

        규칙:
        1. 날짜와 시간은 모두 YYYY-MM-DDTHH:MM:SS 형식을 사용
        2. 가격은 숫자로 변환 (예: "90,000원" → 90000)
        3. 정보가 없는 경우 null 사용
        4. 티켓 상태는 True 또는 False 중 하나로 표시

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

async def crawl_and_parse_concerts():
    crawled_concerts = []
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS) # 캐시사용 X
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Cache-Control': 'no-cache',  # 캐시 무시
        'Cookie': ''  # 기존 쿠키 클리어
    }
    async with AsyncWebCrawler(verbose=True) as crawler:
        # 메인 페이지 크롤링
        url = "https://ticket.interpark.com/webzine/paper/TPNoticeList_iFrame.asp?bbsno=0&pageno=1&stext=&KindOfGoods=&Genre=&sort="

        # iframe 내부 URL 크롤링
        result = await crawler.arun(
            url=url,
            headers=headers,
            css_selector="td.subject",  # 필요한 데이터 선택
            process_iframes=False,
            config=config
        )
        print("actural URL : ",result.url)
        # BeautifulSoup으로 데이터 파싱
        iframe_soup = BeautifulSoup(result.html, "html.parser")
        rows = iframe_soup.select("tr")  # 각 행을 선택 <- 각 행마다 new 마크가 있는지 확인하기 위함

        # 결과 처리
        for row in rows:

            #  각 공연 정보를 저장할 딕셔너리
            concert_info = {}

            # <td class="subject">와 <a> 태그 처리
            subject_tag = row.select_one("td.subject a")
            # 장르 가져오기
            type_tag = row.select_one("td.type")

            # 이 부분에 원하는 타입의 장르만 가져 올 수 있다
            if type_tag:
                concert_info['genre'] = type_tag.text.strip()

            if not concert_info.get('genre','') in ['콘서트','HOT']:
                continue

            if subject_tag:
                concert_info['title'] = subject_tag.get_text(strip=True)
                link = subject_tag.get("href")
                absolute_link = urljoin(url, link)
                concert_info['link'] = absolute_link

                # new <img> 태그 확인 (새로 뜬 공지)
                new_img_tag = row.select_one("td.subject img.ico_new")
                concert_info['is_new'] = bool(new_img_tag)

                if absolute_link:
                    async with AsyncWebCrawler(verbose=True) as crawler_concert:
                        # 메인 페이지 크롤링
                        result_concert = await crawler_concert.arun(url=absolute_link,config=config)

                    # BeautifulSoup 객체 생성
                    soup_concert = BeautifulSoup(result_concert.html, 'html.parser')

                    # <div class="info"> 태그 선택
                    info_div = soup_concert.select_one("div.info")
                    if info_div:
                        poster_tag = info_div.find("img")  # <img> 태그 찾기
                        if poster_tag :
                            img_url = poster_tag.get("src")
                            # 프로토콜이 없는 경우 http: 추가
                            if img_url.startswith("//"):
                                img_url = "https:" + img_url
                            concert_info['poster'] = img_url
                        concert_info['info'] = info_div.text.strip()
                    # <div class="desc"> 태그 선택
                    desc_div = soup_concert.select_one("div.desc")  # 또는 soup.find("div", class_="desc")
                    if desc_div:
                        concert_info['description'] = desc_div.text.strip()

                    # <a class="btn_book"> 태그 처리 예약 버튼
                    book_button_tag = soup_concert.select_one("div.info div.btn a.btn_book")
                    if book_button_tag:
                        book_link = urljoin(url, book_button_tag.get("href"))
                        concert_info['booking_link'] = book_link
                        concert_info['ticket_status'] = "True"
                    else :
                        concert_info['ticket_status'] = "False"

                    # 크롤링된 모든 정보를 하나의 문자열로 변환
                    concert_text = f"""
                    공연명: {concert_info.get('title', '')}
                    공연 포스터: {concert_info.get('poster', '')}
                    장르: {concert_info.get('genre', '')}
                    티켓상태: {concert_info.get('ticket_status', '')}
                    상세정보: {concert_info.get('info', '')}
                    공연설명: {concert_info.get('description', '')}
                    예매링크: {concert_info.get('booking_link', '티켓 미오픈')}
                    """
                    print(concert_text)
                    crawled_concerts.append(concert_text)
    # GPT 파싱 처리
    parser = ConcertParser()
    parsed_results = parser.parse_multiple_concerts(crawled_concerts)
    print(parsed_results)
    return parsed_results

# 실행 코드
async def main():
    # 크롤링 코드 실행
    results = await crawl_and_parse_concerts()

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

    response = requests.post(API_URL, headers=headers, json=file_path)  # `json=data` 사용

    # 응답 확인
    print("응답 코드:", response.status_code)
    print("응답 데이터:", response.json())  # JSON 응답 받기

if __name__ == "__main__":
    asyncio.run(main())

