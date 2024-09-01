import scrapy
from scrapy.crawler import CrawlerProcess
import json
import time

class PokemonScraper(scrapy.Spider):
    name = 'pokemon_scraper'
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def __init__(self):
        self.pokemons = []
        self.processed_pokemon_urls = set()  # Usado para rastrear URLs já processadas

    def parse(self, response):
        # Captura todos os Pokémon na página
        pokemons = response.css('#pokedex tbody tr')
        for pokemon in pokemons:
            number = pokemon.css('td.cell-num span.infocard-cell-data::text').get()
            name = pokemon.css('td.cell-name a.ent-name::text').get()
            link = pokemon.css('td.cell-name a.ent-name::attr(href)').get()
            pokemon_url = response.urljoin(link)

            # Verifica se o número está presente para evitar problemas
            if number and name and pokemon_url:
                if pokemon_url not in self.processed_pokemon_urls:
                    self.processed_pokemon_urls.add(pokemon_url)
                    self.log(f"Capturando Pokémon: {number} - {name}")
                    # Segue o link para a página detalhada do Pokémon
                    yield response.follow(pokemon_url, self.parse_pokemon, meta={
                        'number': number,
                        'name': name,
                        'url': pokemon_url
                    })
                    time.sleep(1)  # Adiciona um pequeno delay entre requests para evitar bloqueios
            else:
                self.log(f"Falha ao capturar dados para o Pokémon: {name}")

    def parse_pokemon(self, response):
        number = response.meta['number']
        name = response.meta['name']
        pokemon_url = response.meta['url']

        # Extrair informações básicas do Pokémon
        pokemon_data = {
            "Id": number,
            "Nome": name,
            "Altura": response.css(
                "table.vitals-table > tbody > tr:contains('Height') > td::text").get(),
            "Peso": response.css(
                "table.vitals-table > tbody > tr:contains('Weight') > td::text").get(),
            "Tipos": [
                tipo.strip() for tipo in response.css(
                    "table.vitals-table > tbody > tr:contains('Type') > td a.type-icon::text"
                ).getall()
            ],
            "URL": pokemon_url
        }

        # Extrair informações de evolução e seguir cada uma
        evolutions = []
        evolution_cards = response.css(
            "div.infocard-list-evo > div.infocard")
        for evolution_card in evolution_cards:
            id_evolution = evolution_card.css('small::text').get()
            name_evolution = evolution_card.css('a.ent-name::text').get()
            url_evolution = evolution_card.css('a.ent-name::attr(href)').get()

            if id_evolution and name_evolution and url_evolution:
                evolution_url_full = response.urljoin(url_evolution)
                evolutions.append({
                    "Id": id_evolution,
                    'Nome': name_evolution,
                    'URL': evolution_url_full
                })

                if evolution_url_full not in self.processed_pokemon_urls:
                    self.processed_pokemon_urls.add(evolution_url_full)
                    yield response.follow(evolution_url_full, self.parse_pokemon)

        # Extrair URLs das habilidades e seguir para cada uma
        ability_urls = response.css(
            'table.vitals-table > tbody > tr:contains("Abilities") td a::attr(href)'
        ).getall()
        for ability_url in ability_urls:
            yield response.follow(ability_url,
                                  self.parse_ability,
                                  meta={
                                      "pokemon_data": pokemon_data,
                                      "Evolucoes": evolutions
                                  })

    def parse_ability(self, response):
        # Extrair informações da habilidade
        ability_data = {
            "Nome": response.css("h1::text").get(),
            "URL": response.url,
            "Descricao": ' '.join(
                response.css(
                    'div > div > h2:contains("Effect") + p::text').getall())
        }

        # Combinar informações do Pokémon com as da habilidade
        pokemon_data = response.meta["pokemon_data"]
        evolutions = response.meta["Evolucoes"]

        # Verificar se o Pokémon já está na lista
        existing_pokemon = next((p for p in self.pokemons if p["Id"] == pokemon_data["Id"]), None)
        if existing_pokemon:
            # Se o Pokémon já existe, adicionar a habilidade à lista de habilidades
            existing_pokemon["Habilidades"].append(ability_data)
        else:
            # Se o Pokémon não existe, adicionar o Pokémon com a primeira habilidade
            pokemon_data["Evolucoes"] = evolutions
            pokemon_data["Habilidades"] = [ability_data]
            self.pokemons.append(pokemon_data)

    def closed(self, reason):
        # Ordena a lista de pokémons pelo número
        sorted_pokemons = sorted(self.pokemons, key=lambda x: int(x['Id']))

        # Salva os pokémons ordenados em um arquivo JSON
        with open('pokemons_sorted.json', 'w') as f:
            json.dump(sorted_pokemons, f, indent=4)

        # Log para indicar que o arquivo foi salvo
        self.log("Arquivo JSON salvo com sucesso.")

# Executa o scraper
process = CrawlerProcess()
process.crawl(PokemonScraper)
process.start()
