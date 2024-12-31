import asyncio
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup  # HTML 파싱용 라이브러리
from urllib.parse import urljoin  # 절대 경로 변환을 위한 라이브러리

async def main():
    async with AsyncWebCrawler(verbose=True) as crawler:
        # 메인 페이지 크롤링
        url = "https://ticket.interpark.com/webzine/paper/TPNoticeList.asp?tid1=in_scroll&tid2=ticketopen&tid3=board_main&tid4=board_main"
        result = await crawler.arun(
            url=url,
            css_selector="iframe#ifRmNotice",  # iframe 태그 선택
            process_iframes=False  # iframe URL만 추출하므로 False
        )

        # BeautifulSoup으로 iframe의 src 추출
        soup = BeautifulSoup(result.html, "html.parser")
        iframe = soup.find("iframe", {"id": "iFrmNotice"})  # id가 iFrmNotice인 iframe 찾기
        iframe_src = iframe["src"] if iframe else None

        if not iframe_src:
            print("iframe src를 찾을 수 없습니다.")
            return

        # URL 결합하여 절대 경로 생성
        iframe_url = urljoin(url, iframe_src)
        print(f"Resolved iframe URL: {iframe_url}")

        # iframe 내부 URL 크롤링
        iframe_result = await crawler.arun(
            url=iframe_url,
            css_selector="td.subject",  # 필요한 데이터 선택
            process_iframes=False
        )

        # BeautifulSoup으로 데이터 파싱
        iframe_soup = BeautifulSoup(iframe_result.html, "html.parser")
        rows = iframe_soup.select("tr")  # 각 행을 선택 <- 각 행마다 new 마크가 있는지 확인하기 위함

        # 결과 처리
        for row in rows:

            # <td class="subject">와 <a> 태그 처리
            subject_tag = row.select_one("td.subject a")

            # 장르 가져오기
            type_tag = row.select_one("td.type")

            # 이 부분에 원하는 타입의 장르만 가져 올 수 있다
            if type_tag:
                print(f"타입 : {type_tag.text.strip()}")

            if subject_tag:
                text = subject_tag.get_text(strip=True)
                link = subject_tag.get("href")
                absolute_link = urljoin(iframe_url, link)

                # <img> 태그 확인
                img_tag = row.select_one("td.subject img.ico_new")
                is_new = bool(img_tag)  # <img> 태그가 있으면 True, 없으면 False

                # 결과 출력
                print(f"텍스트: {text}, 링크: {absolute_link}, New: {is_new}")

                if absolute_link:
                    async with AsyncWebCrawler(verbose=True) as crawler_concert:
                        # 메인 페이지 크롤링
                        url = absolute_link
                        result_concert = await crawler_concert.arun(
                            url=url,
                        )
                    # BeautifulSoup 객체 생성
                    soup_concert = BeautifulSoup(result_concert.html, 'html.parser')

                    # <div class="info"> 태그 선택
                    info_div = soup_concert.select_one("div.info")
                    # <div class="desc"> 태그 선택
                    desc_div = soup_concert.select_one("div.desc")  # 또는 soup.find("div", class_="desc")

                    if info_div:
                        print(info_div.text.strip())  # 텍스트 내용 출력
                    else:
                        print("info 태그를 찾을 수 없습니다.")

                    # <a class="btn_book"> 태그 처리 예약 버튼
                    book_button_tag = soup_concert.select_one("div.info div.btn a.btn_book")
                    if book_button_tag:
                        book_link = urljoin(iframe_url, book_button_tag.get("href"))
                        print(f"예매하기 링크: {book_link}")
                    else :
                        print("아직 티켓이 오픈하지 않았습니다")

                    if desc_div:
                        print(desc_div.text.strip())  # 텍스트 내용 출력
                    else:
                        print("desc 태그를 찾을 수 없습니다.")


if __name__ == "__main__":
    asyncio.run(main())
