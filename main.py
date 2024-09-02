import scrapy
from scrapy.crawler import CrawlerProcess
import json
import time

class PokemonScraper(scrapy.Spider):
    name = 'pokemon_scraper'
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def __init__(self):
        self.pokemons = {}
        self.processed_pokemon_urls = set()

    def parse(self, response):
        pokemons = response.css('#pokedex tbody tr')
        for pokemon in pokemons:
            number = pokemon.css('td.cell-num span.infocard-cell-data::text').get()
            name = pokemon.css('td.cell-name a.ent-name::text').get()
            link = pokemon.css('td.cell-name a.ent-name::attr(href)').get()
            pokemon_url = response.urljoin(link)

            if number and name and pokemon_url:
                if number not in self.pokemons:
                    self.pokemons[number] = {
                        "Id": number,
                        "Nome": name,
                        "URL": pokemon_url,
                        "Altura": "",
                        "Peso": "",
                        "Tipos": [],
                        "Evolucoes": [],
                        "Habilidades": []
                    }
                    self.processed_pokemon_urls.add(pokemon_url)
                    yield response.follow(pokemon_url, self.parse_pokemon, meta={
                        'number': number
                    })
                    time.sleep(1)

    def parse_pokemon(self, response):
        number = response.meta['number']
        pokemon_data = self.pokemons[number]

        pokemon_data["Altura"] = response.css(
            "table.vitals-table > tbody > tr:contains('Height') > td::text").get()
        pokemon_data["Peso"] = response.css(
            "table.vitals-table > tbody > tr:contains('Weight') > td::text").get()
        pokemon_data["Tipos"] = [
            tipo.strip() for tipo in response.css(
                "table.vitals-table > tbody > tr:contains('Type') > td a.type-icon::text"
            ).getall()
        ]

        evolutions = []
        evolution_cards = response.css("div.infocard-list-evo > div.infocard")
        for evolution_card in evolution_cards:
            id_evolution = evolution_card.css('small::text').get().strip("#")
            name_evolution = evolution_card.css('a.ent-name::text').get()
            url_evolution = evolution_card.css('a.ent-name::attr(href)').get()

            if id_evolution and name_evolution and url_evolution:
                evolution_url_full = response.urljoin(url_evolution)
                evolutions.append({
                    "Id": id_evolution,
                    'Nome': name_evolution,
                    'URL': evolution_url_full
                })

                if id_evolution not in self.pokemons:
                    self.pokemons[id_evolution] = {
                        "Id": id_evolution,
                        "Nome": name_evolution,
                        "URL": evolution_url_full,
                        "Altura": "",
                        "Peso": "",
                        "Tipos": [],
                        "Evolucoes": [],
                        "Habilidades": []
                    }
                    yield response.follow(evolution_url_full, self.parse_pokemon, meta={
                        'number': id_evolution
                    })

        pokemon_data["Evolucoes"] = evolutions

        ability_urls = response.css(
            'table.vitals-table > tbody > tr:contains("Abilities") td a::attr(href)'
        ).getall()

        for ability_url in ability_urls:
            yield response.follow(ability_url, self.parse_ability, meta={
                "pokemon_data": pokemon_data,
                "ability_url": ability_url
            })

    def parse_ability(self, response):
        ability_name = response.css("h1::text").get()
        ability_description = ' '.join(
            response.css('div > div > h2:contains("Effect") + p::text').getall()
        )
        ability_url = response.meta["ability_url"]

        pokemon_data = response.meta["pokemon_data"]

        # Evita habilidades duplicadas
        if not any(ability['Nome'] == ability_name for ability in pokemon_data["Habilidades"]):
            pokemon_data["Habilidades"].append({
                "Nome": ability_name,
                "URL": ability_url,
                "Descricao": ability_description
            })

    def closed(self, reason):
        sorted_pokemons = sorted(self.pokemons.values(), key=lambda x: int(x['Id']))
        with open('pokemons_sorted.json', 'w') as f:
            json.dump(sorted_pokemons, f, indent=4)
        self.log("Arquivo JSON salvo com sucesso.")

# Executa o scraper
if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(PokemonScraper)
    process.start()
