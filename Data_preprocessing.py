import pandas as pd
import requests
import json
import os
from datetime import datetime

API_URL = "https://dev.bolmal.shop/save"

results = [
  {
    "concert_name": "전재연 콘서트",
    "concert_poster": "http://ticketimage.interpark.com/TicketImage/notice_poster/20/2025022815122831.jpg",
    "genre": "콘서트",
    "concert_mood": '',
    "concert_style": "Talk Concert",
    "concert_type": "Concert",
    "casting": [
      {
        "name": "김창옥"
      }
    ],
    "performance_rounds": [
      {
        "round": 1,
        "datetime": "2025-04-19T14:00:00"
      },
      {
        "round": 2,
        "datetime": "2025-04-19T18:00:00"
      }
    ],
    "venue": "목포시민문화체육센터 대공연장",
    "running_time": 120,
    "price": {
      "R석": 88000,
      "S석": 66000
    },
    "age_limit": "만 15세 이상",
    "booking_limit": '',
    "selling_platform": "INTERPARK",
    "ticket_status": False,
    "ticket_open_dates": {},
    "booking_link": '',
    "additional_info": "중증장애인(1-3급) 동반1인까지 20% 할인, 경증장애인(4-6급) 및 국가유공자 본인만 20% 할인. 휠체어석은 기획사 전화예매로만 예매 가능. 할인증빙서류 미지참 시 차액 지불 후 티켓 수령 가능."
  }
]

# # 결과 제출
# current_dir = os.getcwd()
# target_dir = os.path.join(current_dir, 'crawl_new_concerts')
# os.makedirs(target_dir, exist_ok=True)
# # 현재 날짜를 파일 이름으로 저장
# current_date = datetime.now().strftime('%Y-%m-%d')  # 'YYYY-MM-DD' 형식
# file_path = os.path.join(target_dir, f'{current_date}.txt')
#
# # TXT 파일로 저장
# with open(file_path, 'w', encoding='utf-8') as f:
#     # 결과를 텍스트 형식으로 변환하여 저장
#     for item in results:
#         f.write(str(item) + '\n')
#
# # HTTP 헤더 설정 (텍스트 형식)
# headers = {"Content-Type": "text/plain"}
#
# # 파일 내용을 읽어서 전송
# with open(file_path, 'r', encoding='utf-8') as f:
#     file_content = f.read()
#
# response = requests.post(API_URL, headers=headers, data=file_content)
#
# # 응답 확인
# print("응답 코드:", response.status_code)
# print("응답 데이터:", response.text)  # 텍스트 응답 받기

# HTTP 헤더 설정 (JSON 형식)
headers = {"Content-Type": "application/json"}
# JSON 파일 열기 및 데이터 로드
with open('crawl_new_concerts/2025-03-02.json', 'r', encoding='utf-8') as f:
    data_list = json.load(f)  # 이제 data_list는 Python 리스트입니다

response = requests.post(API_URL, headers=headers, json=data_list)  # `json=data` 사용

# 응답 확인
print("응답 코드:", response.status_code)