import asyncio
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, parse_qs, urlencode

class InterParkReviewCrawler:
    def __init__(self):
        self.results = []
        self.base_url = "http://ticket.interpark.com/Community/Play/Talk/CommunityList.asp"

    def create_page_url(self, page_no):
        """페이지 URL 생성"""
        params = {
            'bbsno': '10',
            'pageno': str(page_no),
            'stext': '',
            'sflag': '6',
            'cate': 'cate',
            'isBest': 'BEST'
        }
        return f"{self.base_url}?{urlencode(params)}"

    def count_stars(self, td):
        """별점 이미지의 개수를 세는 메소드"""
        star_count = 0
        star_images = td.find_all('img', alt='별점')
        gold_stars = td.find_all('img', src=lambda x: x and 's_g_star_icon.gif' in x)
        star_count = len(star_images) + len(gold_stars)
        return star_count

    def parse_table_row(self, tr):
        """테이블의 각 행을 파싱하는 메소드"""
        row_data = {}

        links = tr.find_all('a')
        if links:
            row_data['title'] = links[0].get_text(strip=True)
            row_data['url'] = links[0].get('href', '')

        star_td = tr.find('td', class_='textsmall')
        if star_td:
            row_data['star_rating'] = self.count_stars(star_td)

        tds = tr.find_all('td', class_='texts')
        for i, td in enumerate(tds):
            column_name = {
                0: 'title',
                1: 'writer',
                2: 'views',
                3: 'likes'
            }.get(i, f'column_{i}')

            row_data[column_name] = td.get_text(strip=True)

        return row_data

    async def crawl_page(self, crawler, page_no):
        # 단일 페이지 크롤링
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
                rows = table.find_all('tr')
                for row in rows:
                    row_data = self.parse_table_row(row)
                    if row_data and len(row_data) > 1:
                        page_results.append(row_data)

            return page_results
        return []

    async def parse_review(self, start_page=1, end_page=5):
        """여러 페이지 순차적 크롤링"""
        async with AsyncWebCrawler(verbose=True) as crawler:
            for page_no in range(start_page, end_page + 1):
                print(f"페이지 {page_no} 크롤링 중...")
                page_results = await self.crawl_page(crawler, page_no)
                self.results.extend(page_results)
                print(f"페이지 {page_no} 완료: {len(page_results)}개의 리뷰 수집")

                # 페이지 간 딜레이 추가 (선택사항)
                await asyncio.sleep(1)

            if self.results:
                df = pd.DataFrame(self.results)
                df = df.drop_duplicates()
                df.to_csv('interpark_reviews.csv', index=False, encoding='utf-8-sig')
                print(f"\n크롤링 완료: 총 {len(df)}개의 리뷰가 저장되었습니다.")

            else:
                print("크롤링된 데이터가 없습니다.")

async def main():
    crawler = InterParkReviewCrawler()
    # 1페이지부터 2981페이지까지 크롤링
    await crawler.parse_review(start_page=1, end_page=2981)

if __name__ == "__main__":
    asyncio.run(main())