import time, sys, datetime
from random import uniform
import random

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

class Crawler_npr:
    def __init__(self, main, site):
        self.driver = main["driver"]
        self.wait = main["wait"]
        self.logging = main["logging"]
        self.es = main["es"]
        self.url = site[0]
        self.categories = site[1]
        self.category = main["category"]

    def parse(self):
        if self.category == "":
            self.category = random.choice(self.categories)
            
        try:
            site_url = self.url + self.category
            self.logging.info(f"parsing started from this url : {site_url}")
            
            page_count = 1
            parsed_urls = []

            while True:
                time.sleep(uniform(1, 2))
                self.driver.get(site_url)
                time.sleep(uniform(1, 2))

                self.logging.debug(f"current page : {page_count}")
                for i in range(page_count-1):
                    self.click_more_btn()

                article_urls = self.get_article_urls(parsed_urls, page_count)

                for article_url in article_urls:

                    if self.es.has_url_parsed("news", article_url):
                        self.logging.info("This url has been parsed.")
                        continue

                    self.get_article_data(article_url)
                    parsed_urls.append(article_url)
                    self.logging.info(f"parsed articles count : {len(parsed_urls)}")

                page_count += 1
        except Exception as e:
            _, _, tb = sys.exc_info()
            self.logging.error(f'parse except,  {tb.tb_lineno},  {e.__str__()}')
    
                

    def click_more_btn(self):
        time.sleep(uniform(1.5, 2))
        self.driver.find_element_by_xpath('//*[@id="main-section"]/div/button').click()
        

    def get_article_urls(self, parsed_urls, page_count):
        '''
        return: [urls] that are not in parsed_urls
        '''
        urls = []
        time.sleep(uniform(1, 2))

        try:
            article_wrap_el = ""

            if page_count == 1:
                article_wrap_el = 'section#main-section > div#overflow > article.item'
            else:
                article_wrap_el = 'div#infinitescrollwrap > div#infinitescroll > article.item'

            articles = self.wait.until(EC.presence_of_all_elements_located((
                By.CSS_SELECTOR,
                article_wrap_el
            )))

            for article in articles:
                try:
                    url = article.find_element(
                        By.CSS_SELECTOR,
                        'h2.title > a'
                    ).get_attribute('href')

                    if not url in parsed_urls:
                        urls.append(url)
                except:
                    print('this element does not have url info')
                    
        except Exception as e:
            _, _, tb = sys.exc_info()
            self.logging.error(f'get article urls except, {str(tb.tb_lineno)}, {e.__str__()}')
            
        finally:
            if len(urls) == 0:
                self.logging.debug('could not parse any urls(same urls)')
            return urls
    
    def get_article_data(self, url):
        self.driver.get(url)
        time.sleep(uniform(2, 3))
        title = ""
        content = ""

        try:
            news_container = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                'section#main-section > article.story'
            )))

            try:
                title = news_container.find_element(
                    By.CSS_SELECTOR,
                    'div.storytitle > h1'
                ).get_attribute('textContent').strip()

                date = news_container.find_element(
                    By.CSS_SELECTOR,
                    'div.dateblock > time'
                ).get_attribute('datetime')

                date = date.replace('T', ' ')

                date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S%z')

                paragraphs = news_container.find_elements(
                    By.CSS_SELECTOR,
                    'article.story > div#storytext > p'
                )

                for paragraph in paragraphs:
                    try:
                        content += paragraph.get_attribute('textContent').strip()
                    except:
                        print("this element does not have text")     

            except Exception as e:
                _, _, tb = sys.exc_info()
                print(e)
                self.logging.error('get article text except ' + str(tb.tb_lineno) + ', ' + e.__str__())
        
            if title and content:
                article = {
                    "site" : "npr",
                    "url" : url,
                    "title" : title,
                    "content" : content,
                    "category" : self.category,
                    "published_at" : date.timestamp(),
                    "crawled_at" : datetime.datetime.now().timestamp(),
                }

                result = self.es.insert_doc("news", article)
                self.logging.debug("insert new doc to es, doc_id : " + result)
            else:
                self.logging.error(f'fail to parse article data from this url, {url}')

        except Exception as e:
                _, _, tb = sys.exc_info()
                self.logging.error('get article data except ' + str(tb.tb_lineno) + ', ' + e.__str__())
