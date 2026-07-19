# -*- coding: utf-8 -*-
import time
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta

class TargetFinder:
    """
    지역 마케팅을 위한 타겟 게시글 발굴 클래스
    키워드 기반으로 블로그, 카페 등의 최신 글을 검색합니다.
    """
    
    
    def __init__(self, driver=None):
        self.driver = driver
        if self.driver:
            self.wait = WebDriverWait(self.driver, 10)
        else:
            self.wait = None
            
    def update_driver(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)
        
    def search_blog_posts(self, keyword, max_posts=10):
        """
        네이버 블로그에서 키워드로 최신 글 검색
        :param keyword: 검색 키워드 (예: "양양 맛집")
        :param max_posts: 수집할 최대 게시글 수
        :return: 게시글 정보 리스트 [{'title', 'link', 'author', 'date'}]
        """
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            # 최근 1개월 이내 필터 적용 (30일 전 ~ 오늘)
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # 정확도순 정렬 (orderBy=simul), 기간 설정 (rangeType=PERIOD)
            url = f"https://section.blog.naver.com/Search/Post.naver?pageNo=1&rangeType=PERIOD&orderBy=simul&startDate={start_date}&endDate={end_date}&keyword={encoded_keyword}"
            self.driver.get(url)
            time.sleep(2)
            
            results = []
            
            # 게시글 리스트 요소 찾기
            # (네이버 블로그 검색 페이지 구조에 따라 선택자 조정 필요)
            # 보통 user_info 클래스나 list_search_post 클래스 등을 사용
            
            # 2024년 기준 추정 선택자 (실제 확인 필요)
            # list_search_post 내의 요소들 순회
            
            # 명시적 대기
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "info_post")))
            
            posts = self.driver.find_elements(By.CLASS_NAME, "list_search_post")
            
            for post in posts[:max_posts]:
                try:
                    # 제목 및 링크 추출 (desc_inner 클래스가 a 태그임)
                    title_link_elem = post.find_element(By.CLASS_NAME, "desc_inner")
                    link = title_link_elem.get_attribute("href")
                    title = title_link_elem.text
                    
                    author_elem = post.find_element(By.CLASS_NAME, "name_author")
                    author = author_elem.text
                    
                    date_elem = post.find_element(By.CLASS_NAME, "date")
                    date = date_elem.text
                    
                    results.append({
                        "title": title,
                        "link": link,
                        "author": author,
                        "date": date,
                        "platform": "blog"
                    })
                except Exception as e:
                    print(f"게시글 파싱 중 오류: {e}")
                    continue
                    
            print(f"✅ 블로그 검색 완료: {keyword} -> {len(results)}개 발견")
            return results
            
        except Exception as e:
            print(f"❌ 블로그 검색 실패: {e}")
            return []

    def search_cafe_posts(self, keyword, max_posts=10):
        """
        네이버 카페에서 키워드로 최신 글 검색 (전체 카페 대상)
        """
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            # 카페 최근 1개월 이내 필터 적용 (30일 전)
            start_date_cafe = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            # 카페 전체 글 검색 (정확도순 od=1, 직접입력 pr=7, 시작일 p_dt)
            url = f"https://section.cafe.naver.com/ca-fe/home/search/articles?q={encoded_keyword}&od=1&pr=7&p_dt={start_date_cafe}"
            self.driver.get(url)
            time.sleep(3)
            
            results = []
            
            # 리스트 로딩 대기
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.article_item_wrap, li.item_list")))
            except:
                pass
            
            # Selectors based on verified DOM
            # Container: div.article_item_wrap
            posts = self.driver.find_elements(By.CSS_SELECTOR, "div.article_item_wrap, li.item_list")
            
            for post in posts[:max_posts]:
                try:
                    # Title & Link
                    # Selector: a:not(.cafe_info)
                    title_elem = post.find_element(By.CSS_SELECTOR, "a:not(.cafe_info)")
                    title = title_elem.text
                    link = title_elem.get_attribute("href")
                    
                    if not link or "javascript" in link:
                        continue

                    # Cafe Name
                    # Selector: a.cafe_info span.cafe_name
                    cafe_name = "네이버 카페"
                    try:
                        cafe_name = post.find_element(By.CSS_SELECTOR, "a.cafe_info span.cafe_name").text
                    except:
                        try:
                            cafe_name = post.find_element(By.CSS_SELECTOR, "span.cafe_name").text
                        except:
                            pass
                        
                    # Date
                    date = "최근"
                    try:
                        date = post.find_element(By.CSS_SELECTOR, "a.cafe_info span.date").text
                    except:
                        try:
                             date = post.find_element(By.CSS_SELECTOR, "span.date").text
                        except:
                            pass
                        
                    results.append({
                        "title": title,
                        "link": link,
                        "author": cafe_name,
                        "date": date,
                        "platform": "cafe"
                    })
                except Exception as e:
                    continue
            
            print(f"✅ 카페 검색 완료: {keyword} -> {len(results)}개 발견")
            return results
            
        except Exception as e:
            print(f"❌ 카페 검색 실패: {e}")
            return []

    def search_band_posts(self, keyword, max_posts=10):
        """
        네이버 밴드에서 키워드로 최신 '게시글' 검색
        """
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            # 밴드 '게시글' 검색
            url = f"https://band.us/search/post?keyword={encoded_keyword}"
            self.driver.get(url)
            time.sleep(3)
            
            results = []
            
            # 리스트 로딩 대기
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-viewname='DPostItemView'], div.cPost, li.post_item")))
            except:
                pass
                
            # Primary choice: verified selector for lists
            posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-viewname='DPostItemView'], div.cPost, li.post_item")
            
            # Fallback: if user is not logged in / redirected, maybe we are on 'All' or 'Band' tab which has different structure
            if not posts:
                 posts = self.driver.find_elements(By.CSS_SELECTOR, "div.cPostContent, div.post_item")

            for post in posts[:max_posts]:
                try:
                    # Link
                    link = ""
                    # 1. Try finding a time/date link (usually permalink)
                    try:
                        link = post.find_element(By.CSS_SELECTOR, "a.time, a.cDate").get_attribute("href")
                    except:
                        # 2. Try generic link check
                        links = post.find_elements(By.TAG_NAME, "a")
                        for l in links:
                            href = l.get_attribute("href")
                            if href and "/post/" in href:
                                link = href
                                break
                    
                    if not link:
                         continue

                    # Title / Content
                    title = "밴드 게시글"
                    try:
                        # cPostContent or similar
                        text_elem = post.find_element(By.CSS_SELECTOR, "div.postText, div.cPostContent, p.txt")
                        title = text_elem.text[:40].replace("\n", " ") + "..."
                    except:
                        pass
                    
                    # Band Name
                    band_name = "밴드"
                    try:
                        band_name = post.find_element(By.CSS_SELECTOR, "a.bandName, strong.name").text
                    except:
                        pass
                    
                    # Date
                    date = "최근"
                    try:
                        date = post.find_element(By.CSS_SELECTOR, "time.time, span.time").text
                    except:
                        pass
                        
                    results.append({
                        "title": title,
                        "link": link,
                        "author": band_name,
                        "date": date,
                        "platform": "band"
                    })
                except Exception as e:
                    continue
                    
            print(f"✅ 밴드 검색 완료: {keyword} -> {len(results)}개 발견")
            return results
            
        except Exception as e:
            print(f"❌ 밴드 검색 실패: {e}")
            return []
