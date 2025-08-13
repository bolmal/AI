# -*- coding: utf-8 -*-
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from datetime import datetime

from models.schemas import Concert
from parseDetail import parseDetail


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

    @staticmethod
    def make_json_with_langchain(concert_texts: list[str], api_key: str) -> list[dict]:
        # 모델 초기화
        model = ChatOpenAI(api_key=api_key, model="gpt-4-turbo", temperature=0.1)

        # 출력 파서 설정 (Pydantic 모델과 연결)
        parser = PydanticOutputParser(pydantic_object=Concert)

        prompt = ChatPromptTemplate.from_template(
            """
            You are an expert Korean concert information parser.
            Your task is to extract structured data from the user's concert information text and format it according to the provided schema.

            Follow these general rules:
            - Convert monetary values to integers (e.g., "90,000원" -> 90000).
            - If information for an optional field is not present in the text, use null.
            - Carefully determine the ticket_status based on the current date and sale dates.
            - Ensure all generated URLs are valid and working.

            {format_instructions}

            For the following fields, you MUST use one of the provided values. Do not use any other value.

            For the 'genre' field, select only one from the following:
            ["발라드","댄스","랩/힙합","아이돌","R&B/Soul","인디음악","록/메탈","성인가요/트로트",
                "포크/블루스","일렉트로니카","클래식","재즈","J-POP","POP","키즈","CCM","국악"]

            For the 'concert_mood' field, select only one from the following:
            ["Emotional", "Energetic", "Dreamy", "Grand", "Calm", "Fun", "Intense"]

            For the 'concert_style' field, select only one from the following:
            ["Live Band", "Acoustic", "Orchestra", "Solo Performance", "Dance Performance", "Theatrical Concert"]

            For the 'concert_type' field, select only one from the following:
            ["Festival", "Concert", "Music Show", "Fan Meeting", "Talk Concert"]

            Now, parse the following concert information:
            ---
            {concert_text}
            """,
            # partial_variables를 사용해 파서가 만든 포맷팅 지침을 프롬프트에 미리 삽입합니다.
            partial_variables={
                "format_instructions": parser.get_format_instructions(),
            },
        )

        # 3. LCEL로 컴포넌트들을 파이프처럼 연결
        chain = prompt | model | parser

        parsed_results = []
        for text in concert_texts:
            print(f"🔍 Parsing with LangChain...\n{text[:50]}...")
            try:
                # 체인 실행
                parsed = chain.invoke({"concert_text": text})
                # Pydantic 모델을 dict로 변환하여 저장
                parsed_results.append(parsed.model_dump(mode='json'))
            except Exception as e:
                print(f"❌ Error parsing concert with LangChain: {e}")
                
        print("✅ 모든 공연 json으로 변환 완료 (LangChain)")
        return parsed_results
    

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
