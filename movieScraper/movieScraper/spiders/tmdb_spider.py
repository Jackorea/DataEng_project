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

        # Extract genres from the genre <a> elements
        genres = response.css('a[href*="/genre/"]::text').extract()

        # Extract runtime
        runtime = response.css("span.runtime::text").extract_first()
        if runtime:
            runtime = runtime.strip()  # Remove any leading/trailing whitespace

        # Extract release date
        release_date = response.css("span.release::text").extract_first()
        if release_date:
            release_date = release_date.strip()  # Clean up the whitespace

        # Extract budget
        #budget_element = response.xpath("//p[strong[bdi[text()='Budget']]]/text()").get()
        #if budget_element:
        #    budget = budget_element.strip().replace(",", "").replace("$", "").replace(".00", "")
        #    budget = int(budget) if budget.isdigit() else budget
        #else:
        #    budget = None

        # Extract keywords
        keywords = response.css("section.keywords.right_column ul li a::text").extract()


        # Extract langue d'origine
        langue_element = response.xpath("//section[@class='facts left_column']/p[strong[bdi[contains(text(),\"Langue d'origine\")]]]/text()").get()
        if langue_element:
            langue = langue_element.strip()
        else:
            langue = None

        # Extract budget
        budget_element = response.xpath("//section[@class='facts left_column']/p[strong[bdi[contains(text(),'Budget')]]]/text()").get()
        if budget_element:
            budget = budget_element.strip().replace(",", "").replace("$", "").replace(".00", "")
            budget = int(budget) if budget.isdigit() else budget
        else:
            budget = None

        # Extract recette (revenue)
        recette_element = response.xpath("//section[@class='facts left_column']/p[strong[bdi[contains(text(),'Recette')]]]/text()").get()
        if recette_element:
            recette = recette_element.strip().replace(",", "").replace("$", "").replace(".00", "")
            recette = int(recette) if recette.isdigit() else recette
        else:
            recette = None

        # Extract score percentage (data-percent)
        score = response.css("div.user_score_chart::attr(data-percent)").get()
        if score:
            score = int(score)  # Convert to integer

        # Extract actor names
        actors = response.css("li.card p a::text").extract()

        # Extract director's name
        director = response.xpath("//li[p[@class='character' and contains(text(), 'Director')]]/p/a/text()").get()

        # Yield the data as a dictionary
        yield {
            "title": title,
            "genres": genres,
            "runtime": runtime,
            "release_date": release_date,
            "keywords": keywords,
            "langue_origine": langue,
            "budget_usd": budget,
            "recette_usd": recette,
            "rating": score,
            "actors": actors,
            "director": director
        }