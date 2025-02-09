import pandas as pd
import requests

API_URL = "https://dev.bolmal.shop/concerts/save"

# HTTP 헤더 설정 (JSON 형식)
headers = {"Content-Type": "application/json"}

data = [{
 "concert_name": "2025 2NE1 CONCERT [WELCOME BACK] ENCORE IN SEOUL",
 "concert_poster": "https://ticketimage.interpark.com/Play/image/large/25/25001426_p.gif",
 "performance_rounds": [
   {
     "round": 1,
     "datetime": "2025-04-12T18:00:00"
   },
   {
     "round": 2,
     "datetime": "2025-04-13T17:00:00"
   }
 ],
 "venue": "KSPO DOME",
 "running_time": '',
 "price": {},
 "age_limit": '',
 "booking_limit": "회차당 1인 2매까지 예매 가능",
 "selling_platform": "INTERPARK",
 "ticket_status": True,
 "ticket_open_dates": {
   "round": "2025-02-10T20:00:00"
 },
 "booking_link": "http://tickets.interpark.com/contents/bridge/25001426",
 "additional_info": "설명"
}]

response = requests.post(API_URL, headers=headers, json=data)  # `json=data` 사용

