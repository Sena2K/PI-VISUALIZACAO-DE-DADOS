import scrapy
from scrapy.crawler import CrawlerProcess
import json

class PokemonScraper(scrapy.Spider):
    name = 'pokemon_scraper'
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def __init__(self):
        self.pokemons = []

    def parse(self, response):
        # Captura todos os Pokémon na página
        pokemons = response.css('#pokedex tbody tr')
        for pokemon in pokemons:
            number = pokemon.css('td.cell-num span.infocard-cell-data::text').get()
            name = pokemon.css('td.cell-name a.ent-name::text').get()
            link = pokemon.css('td.cell-name a.ent-name::attr(href)').get()
            pokemon_url = response.urljoin(link)

            # Log para verificar se está capturando os Pokémon
            self.log(f"Capturando Pokémon: {number} - {name}")

            # Segue o link para a página detalhada do Pokémon
            yield response.follow(pokemon_url, self.parse_pokemon, meta={
                'number': number,
                'name': name,
                'url': pokemon_url
            })

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
            "URL": pokemon_url,
            "Evolucoes": [],
            "Habilidades": []
        }

        # Extrair informações de evolução
        evolution_cards = response.css(
            "div.infocard-list-evo > div.infocard:not(:first-child)")
        for evolution_card in evolution_cards:
            id_evolution = evolution_card.css('small::text').get()
            name_evolution = evolution_card.css('a.ent-name::text').get()
            url_evolution = evolution_card.css('a.ent-name::attr(href)').get()

            if id_evolution and name_evolution and url_evolution:
                pokemon_data["Evolucoes"].append({
                    "Id": id_evolution.strip('#'),
                    'Nome': name_evolution,
                    'URL': response.urljoin(url_evolution)
                })

        # Armazena as URLs das habilidades para processamento posterior
        ability_urls = response.css(
            'table.vitals-table > tbody > tr:contains("Abilities") td a::attr(href)'
        ).getall()

        # Se houver habilidades, processa-as
        if ability_urls:
            for ability_url in ability_urls:
                yield response.follow(ability_url, self.parse_ability, meta={
                    "pokemon_data": pokemon_data,
                    "ability_urls": ability_urls
                })
        else:
            # Se não houver habilidades, salva o Pokémon diretamente
            self.pokemons.append(pokemon_data)

    def parse_ability(self, response):
        # Extrair informações da habilidade
        ability_data = {
            "Nome": response.css("h1::text").get(),
            "URL": response.url,
            "Descricao": ' '.join(
                response.css('div > div > p::text').getall())
        }

        # Recuperar as informações do Pokémon
        pokemon_data = response.meta["pokemon_data"]
        ability_urls = response.meta["ability_urls"]

        # Adicionar a habilidade à lista de habilidades do Pokémon
        pokemon_data["Habilidades"].append(ability_data)

        # Verifica se todas as habilidades foram processadas
        if len(pokemon_data["Habilidades"]) == len(ability_urls):
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
