# -*- coding: utf-8 -*-
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

class ConcertParser:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.system_message = """You are a Korean concert information parser.
            Your task is to extract structured data from concert information text.
            Always output valid JSON in Korean following this exact format:
            {
                "concert_name": string,
                "concert_poster": string | null,
                "genre": string,
                "concert_mood": string,
                "concert_style": string,
                "concert_type": string,
                "casting": [{"name": string}],
                "performance_rounds": [{"round": number, "datetime": "YYYY-MM-DDTHH:MM:SS"}],
                "venue": string | null,
                "running_time": number | null,
                "price": {"type": number},
                "age_limit": string | null,
                "booking_limit": string | null,
                "selling_platform": "INTERPARK",
                "ticket_status": boolean,
                "ticket_open_dates": {"round": "YYYY-MM-DDTHH:MM:SS"},
                "booking_link": string | null,
            \}"""

    def singleConcertToJson(self, concert_text: str) -> dict:
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
                model="gpt-4-turbo",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ Error parsing concert: {e}")
            return None

def makeJson(finalOutput: list[str],api_key: str) -> list[str]:
    parser = ConcertParser(api_key)
    parsed_results = []

    for singleConcet in finalOutput:
        print(f"🔍 Parsing...\n{singleConcet[:50]}...")
        parsed = parser.singleConcertToJson(singleConcet)
        if parsed:
            parsed_results.append(parsed)

    print("✅ 모든 공연 json으로 변환 완료")
    return parsed_results

# 실행 예시
# makeJson(finalOutput,api_key=OPENAI_API_KEY)
