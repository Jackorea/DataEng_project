import scrapy
from scrapy.http import HtmlResponse, Request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import time

class TmdbSpiderSpider(scrapy.Spider):
    name = "tmdb_spider"
    allowed_domains = ["themoviedb.org"]
    start_urls = ["https://www.themoviedb.org/movie?language=fr"]

    def __init__(self, *args, **kwargs):
        super(TmdbSpiderSpider, self).__init__(*args, **kwargs)
        # Initialize Selenium WebDriver
        self.driver = webdriver.Chrome()

    def parse(self, response):
        try:
            self.driver.get(response.url)

            # Step 1: Initial click on "Afficher davantage" if present
            try:
                load_more_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Afficher davantage')]"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
                load_more_button.click()
                time.sleep(2)  # Allow short time for content to load
                self.logger.info("Clicked 'Afficher davantage' to start infinite scrolling.")
            except TimeoutException:
                self.logger.info("No initial 'Afficher davantage' button found. Proceeding to scroll.")

            # Step 2: Infinite scroll to load up to 100 movies
            total_movies = 0  # Number of movies currently loaded
            last_movie_count = -1  # To track if new movies are being added
            movie_limit = 1000  # Limit the number of movies to crawl

            while total_movies < movie_limit:
                # Scroll to the bottom of the page
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Short wait to allow content to load

                # Check the number of loaded movies
                total_movies = len(self.driver.find_elements(By.CSS_SELECTOR, "div.card.style_1"))
                
                # Log progress
                self.logger.info(f"Loaded {total_movies} movies so far.")

                # Stop if no new movies are being added
                if total_movies == last_movie_count:
                    self.logger.info("No more new movies are being loaded. Stopping.")
                    break

                # Update last movie count
                last_movie_count = total_movies

            # Step 3: Pass the fully loaded page's HTML to Scrapy
            html = self.driver.page_source
            selenium_response = HtmlResponse(url=response.url, body=html, encoding='utf-8')

            # Scrape up to 100 movies
            movie_links = selenium_response.css("div.card.style_1 a.image::attr(href)").extract()[:movie_limit]
            self.logger.info(f"Found a total of {len(movie_links)} movies.")
            for link in movie_links:
                full_url = response.urljoin(link)
                yield Request(full_url, callback=self.parse_category)

        finally:
            self.driver.quit()  # Ensure the driver always quits

    def parse_category(self, response):
        # Extract data from the movie page
        title = response.css("h2 a::text").get()
        genres = response.css('a[href*="/genre/"]::text').extract()
        runtime = response.css("span.runtime::text").get()
        release_date = response.css("span.release::text").get()
        keywords = response.css("section.keywords.right_column ul li a::text").extract()


        # Extract language
        langue = response.xpath(
            "//section[@class='facts left_column']/p[strong[bdi[contains(text(),\"Langue d'origine\")]]]/text()"
        ).get()
        langue = langue.strip() if langue else None

        # Extract budget
        budget = response.xpath(
            "//section[@class='facts left_column']/p[strong[bdi[contains(text(),'Budget')]]]/text()"
        ).get()
        if budget:
            try:
                budget = int(budget.strip().replace("$", "").replace(",", "").replace(".00", ""))
            except ValueError:
                budget = None

        # Extract revenue (recette)
        recette = response.xpath(
            "//section[@class='facts left_column']/p[strong[bdi[contains(text(),'Recette')]]]/text()"
        ).get()
        if recette:
            try:
                recette = int(recette.strip().replace("$", "").replace(",", "").replace(".00", ""))
            except ValueError:
                recette = None


        # Extract score
        score = response.css("div.user_score_chart::attr(data-percent)").get()
        score = int(score) if score else None

        # Extract actors
        actors = response.css("li.card p a::text").extract()

        # Extract director
        director = response.xpath("//li[p[@class='character' and contains(text(), 'Director')]]/p/a/text()").get()

        # Yield the data as a dictionary
        yield {
            "title": title,
            "genres": genres,
            "runtime": runtime.strip() if runtime else None,
            "release_date": release_date.strip() if release_date else None,
            "keywords": keywords,
            "langue_origine": langue.strip() if langue else None,
            "budget_usd": budget,
            "recette_usd": recette,
            "rating": score,
            "actors": actors,
            "director": director,
        }
