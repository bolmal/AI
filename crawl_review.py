import asyncio
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, parse_qs, urlencode

class InterParkReviewCrawler:
    def __init__(self):
        self.results = []
        self.base_url = "http://ticket.interpark.com/Community/Play/Talk/"
        self.crawler = None  # 크롤러 인스턴스를 클래스 레벨에서 관리

    def create_page_url(self, page_no):
        """페이지 URL 생성"""
        params = {
            'bbsno': '10',
            'pageno': str(page_no),
            'stext': '',
            'groupcode': '01003',  # 콘서트
            'sflag': '',
            'sort': 'New',  # 최신순 정렬
            'cate': '01003',  # 콘서트
            'seq': '0',
            'isBest': 'N',  # 일반 리뷰
            'bestOnoff': 'N',  # 베스트 OFF
            'categorycode': '',  # 카테고리 코드
            'stycode': '',  # 스타일 코드
            'noticeYN': 'N'  # 공지사항 제외
        }
        return f"{self.base_url+'CommunityList.asp'}?{urlencode(params)}"

    # 별점 이미지의 개수를 세는 메소드
    def count_stars(self, td):
        star_count = 0
        star_images = td.find_all('img', alt='별점')
        star_count = len(star_images)
        return star_count

    # 테이블의 각 행을 파싱
    async def parse_table_row(self, tr):
        row_data = {}
        try :
            # 링크 정보 추출
            links = tr.find_all('a')
            print(f"links : {links}\n")

            if not links or len(links) < 2:
                return None  # 유효하지 않은 행은 건너뛰기

            row_data['url'] = urljoin(self.base_url, links[1].get('href', ''))
            print(f"real_rink : {row_data['url']}")
            if not row_data['url']:  # URL이 없으면 건너뛰기
                return None

            # 별점 추출
            star_td = tr.find('td', class_='textsmall')
            if star_td:
                row_data['star_rating'] = self.count_stars(star_td)

            # 기타 정보 추출
            texts_tds = tr.find_all('td', class_='texts')
            textsmall_tds = tr.find_all('td', class_='textsmall')
            tds = texts_tds + textsmall_tds
            for i, td in enumerate(tds):
                column_name = {
                    0: 'title',
                    1: 'review',
                    2: 'view',
                    3: 'likes',
                    4: 'stars',
                    5: 'blank',
                    6: 'userid',
                    7: 'date'
                }.get(i, f'column_{i}')

                row_data[column_name] = td.get_text(strip=True)

            # URL이 있는 경우 추가 크롤링 수행
            if row_data.get('url'):  # 'url' 키 존재 여부 및 값 체크
                detailed_data = await self.crawl_review_detail_page(url=row_data['url'])
                if detailed_data is not None:
                    row_data['title']=detailed_data
                else:
                    print(f"Failed to crawl detail page for URL: {row_data['url']}")
                    row_data['title'] = 'NO NAME'

        except Exception as e:
            print(f"행 파싱 중 에러 발생: {str(e)}")
            return None
        return row_data

    # 리뷰 상세 페이지를 크롤링하는 메소드
    async def crawl_review_detail_page(self, url):
        detailed_data = None
        try:
            # 요청 및 파싱
            result = await self.crawler.arun(
                url=url,
                css_selector="text",
                process_iframes=True
            )

            if result and result.html:  # 결과와 HTML 내용이 유효한지 확인
                soup = BeautifulSoup(result.html, 'html.parser')

                # 모든 <a> 태그에서 링크(href) 추출
                links = soup.find_all('a')
                print(f"review_detail_rink : {links}")
                for link in links:
                    href = link.get('href')
                    if href and 'GoodsCode=' in href:
                        # URL 파싱하여 GoodsCode 값 추출
                        concert_link = href
                        print(f"concert_link : {href}\n")
                        concert_title = await self.crawl_review_concert_title_page(url=concert_link)
                        print(f"concert_title : {concert_title}\n")
                        detailed_data = concert_title
                        break
            else:
                print(f"No valid HTML content for URL: {url}")
                detailed_data = None

        except Exception as e:
            print(f"Error crawling {url}: {e}")
            detailed_data = None  # 오류 시 기본값 설정

        return detailed_data

    # 리뷰한 콘서트 제목 크롤링
    async def crawl_review_concert_title_page(self, url):
        try :
            result = await self.crawler.arun(url=url)
            if result and result.html:
                soup = BeautifulSoup(result.html, 'html.parser')
                concert_title = soup.find('h2', class_='prdTitle')
                if concert_title:
                    print(f"concert_title : {concert_title}\n")
                    print(f"concert_title : {concert_title.get_text().strip()}\n")
                    return concert_title.get_text().strip()
            else :
                print("공연 제목 X")
        except Exception as e:
            print(f"공연 제목 크롤링 중 에러 발생: {str(e)}")
            return None


    # 단일 페이지 크롤링
    async def crawl_page(self, crawler, page_no):
        url = self.create_page_url(page_no)
        result = await crawler.arun(
            url=url,
            css_selector="table",
            process_iframes=True
        )
        if result and result.html:
            soup = BeautifulSoup(result.html, 'html.parser')
            target_tables = soup.find_all('table', attrs={'width': '100%', 'border': '0'})

            page_results = []
            for table in target_tables:
                rows = table.select('tbody > tr')
                for row in rows:
                    row_data = await self.parse_table_row(row)
                    if row_data is not None:
                        page_results.append(row_data)

            return page_results
        return []

    """여러 페이지 순차적 크롤링"""
    async def parse_review(self, start_page=1, end_page=1):
        async with AsyncWebCrawler(verbose=True) as crawler:
            self.crawler = crawler
            for page_no in range(start_page, end_page + 1):
                print(f"페이지 {page_no} 크롤링 중...")
                page_results = await self.crawl_page(crawler, page_no)
                self.results.extend(page_results)
                print(f"페이지 {page_no} 완료: {len(page_results)}개의 리뷰 수집")
                await asyncio.sleep(1)

            # 결과 저장
            if self.results:
                df = pd.DataFrame(self.results)
                df = df.drop_duplicates()
                filter_df = df.iloc[7:22, :10]  # :8은 column_8 이전의 열까지만 선택
                filter_df.to_csv('interpark_reviews.csv', index=False, encoding='utf-8-sig')
                print(f"\n크롤링 완료: 총 {len(filter_df)}개의 리뷰가 저장되었습니다.")

            else:
                print("크롤링된 데이터가 없습니다.")

async def main():
    crawler = InterParkReviewCrawler()
    # 1페이지부터 n페이지까지 크롤링
    await crawler.parse_review(start_page=1, end_page=1)

if __name__ == "__main__":
    asyncio.run(main())