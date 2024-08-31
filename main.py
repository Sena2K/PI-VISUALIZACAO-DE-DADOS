import scrapy
from scrapy.crawler import CrawlerProcess

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

            # Extração dos tipos
            types = ", ".join(pokemon.css('td.cell-icon a.type-icon::text').getall())

            # Log para verificar se está capturando os Pokémon
            self.log(f"Capturando Pokémon: {number} - {name}")

            # Segue o link para a página detalhada do Pokémon
            yield response.follow(pokemon_url, self.parse_pokemon, meta={
                'number': number,
                'name': name,
                'url': pokemon_url,
                'types': types
            })

    def parse_pokemon(self, response):
        number = response.meta['number']
        name = response.meta['name']
        pokemon_url = response.meta['url']
        types = response.meta['types']

        # Extração da altura e peso
        height = response.css('.vitals-table tr:contains("Height") td::text').get().strip()
        weight = response.css('.vitals-table tr:contains("Weight") td::text').get().strip()

        # Extração das evoluções
        evolutions = []
        for evo in response.css('.infocard-list-evo .infocard'):
            evo_number = evo.css('.text-muted small::text').get()
            evo_name = evo.css('.ent-name::text').get()
            evo_link = response.urljoin(evo.css('a::attr(href)').get())

            if evo_number and evo_name:
                evolutions.append({
                    'number': evo_number,
                    'name': evo_name,
                    'url': evo_link
                })

        # Extração das habilidades
        abilities = []
        for ability in response.css('.vitals-table tr:contains("Abilities") td a'):
            ability_name = ability.css('::text').get()
            ability_url = response.urljoin(ability.css('::attr(href)').get())
            abilities.append({
                'name': ability_name,
                'url': ability_url
            })

        # Adiciona o Pokémon na lista de pokémons
        self.pokemons.append({
            'number': number,
            'name': name,
            'url': pokemon_url,
            'types': types,
            'height_cm': height,
            'weight_kg': weight,
            'evolutions': evolutions,
            'abilities': abilities,
        })

        # Continua para processar as habilidades
        for ability in abilities:
            yield response.follow(ability['url'], self.parse_ability, meta={
                'pokemon_name': name,
                'ability_name': ability['name'],
                'ability_url': ability['url']
            })

    def parse_ability(self, response):
        # Captura a descrição da habilidade
        description = response.css('.span-lg-6 p::text').get()

        # Recupera as informações do Pokémon e habilidade do meta
        pokemon_name = response.meta['pokemon_name']
        ability_name = response.meta['ability_name']
        ability_url = response.meta['ability_url']

        # Log para verificar as habilidades capturadas
        self.log(f"Capturando habilidade: {ability_name} de {pokemon_name}")

        # Salva a habilidade com a descrição
        yield {
            'pokemon_name': pokemon_name,
            'ability_name': ability_name,
            'description': description.strip() if description else "No description available",
            'url': ability_url
        }

    def closed(self, reason):
        # Ordena a lista de pokémons pelo número
        sorted_pokemons = sorted(self.pokemons, key=lambda x: int(x['number']))

        # Log ou salva os pokémons ordenados
        for pokemon in sorted_pokemons:
            self.log(f"Pokémon {pokemon['number']}: {pokemon['name']}")

        # Aqui você pode optar por salvar os dados ordenados em um arquivo JSON ou CSV
        # Por exemplo, para salvar como JSON:
        import json
        with open('pokemons_sorted.json', 'w') as f:
            json.dump(sorted_pokemons, f, indent=4)

