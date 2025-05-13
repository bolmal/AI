import json
import re

file_path = "crawl_new_concerts/2025-05-12.json"

patterns = {
    '공연명': re.compile(r'공연명:\s*(.*?)\s*(?=\n|$)'),
    '티켓상태': re.compile(r'티켓상태:\s*(.*?)\s*(?=\n|$)'),
    '예매링크': re.compile(r'예매링크:\s*(.*?)\s*(?=\n|$)'),
    '공연요약': re.compile(r'공연요약:\s*(.*?)\s*(?=\n|$)')
}
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

parsed_data = []

for text_block in data:  # 각 요소는 문자열
    result = {}
    for line in text_block.splitlines():
        line = line.strip()
        for key, pattern in patterns.items():
            match = pattern.search(line)
            if match:
                result[key] = match.group(1).strip()
    # 매칭된 데이터가 있을 경우 결과 리스트에 추가
    if result:
        parsed_data.append(result)
# 결과 출력
for entry in parsed_data:
    print(entry)
