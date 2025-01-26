import scrapy
from scrapy.http import Request

class TmdbSpiderSpider(scrapy.Spider):
    name = "tmdb_spider"
    allowed_domains = ["themoviedb.org"]
    start_urls = ["https://www.themoviedb.org/movie"]

    def parse(self, response):
        movie_links = response.css("div.card.style_1 a.image::attr(href)").extract() #extract all the movie links

        #Iterates the movie links
        for link in movie_links: 
            full_url = response.urljoin(link)
            yield Request(full_url, callback=self.parse_category)

    def parse_category(self, response):
        # Extraire le nom du film depuis la balise <a> à l'intérieur de <h2>
        title = response.css("h2 a::text").extract_first()

        # Extraire la date de sortie si nécessaire
        #release_date = response.css("span.tag.release_date::text").extract_first()

        yield {
            "title": title,
        }