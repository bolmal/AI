import requests
from bs4 import BeautifulSoup
import re

def parseDetail(concertList:list[str]) -> list[str]:
    # 결과 저장용 리스트
    results = []

    # 브라우저 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    # 각 공연 정보 처리
    for concert in concertList:
        match = re.search(r"https?://\S+", concert)
        if not match:
            results.append("[링크 없음]")
            continue

        url = match.group(0).strip()

        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, "html.parser")

            # 상세 설명 텍스트
            info = soup.find(class_="DetailInfo_infoWrap__1BtFi")
            info_text = info.get_text(strip=True) if info else "[상세정보 없음]"

            # 이미지 링크
            image = soup.find(class_="DetailSummary_imageContainer__OmWus")
            img_tag = image.find("img") if image else None
            img_src = img_tag["src"] if img_tag and img_tag.has_attr("src") else "[이미지 없음]"

            combined = f"공연 URL: {url}\n공연 설명:\n{info_text}\n이미지 링크: {img_src}"
            results.append(combined)

        except Exception as e:
            results.append(f"[에러] {url} 처리 중 오류 발생: {str(e)}")

    print("✅ 상세 크롤링 완료")
    return results
