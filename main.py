import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request
import json
import pandas as pd
import re

class PokemonItem(scrapy.Item):
    number = scrapy.Field()
    name = scrapy.Field()
    url = scrapy.Field()
    types = scrapy.Field()
    height_cm = scrapy.Field()
    weight_kg = scrapy.Field()
    next_evolutions = scrapy.Field()
    abilities = scrapy.Field()

class PokemonScrapper(scrapy.Spider):
    name = 'pokemon_scrapper'
    start_urls = ["https://pokemondb.net/pokedex/all"]
    items = []  # Lista para armazenar os itens coletados

    def parse(self, response):
        pokemons = response.css('#pokedex > tbody > tr')
        for pokemon in pokemons:
            number = pokemon.css('td.cell-num span.infocard-cell-data::text').get()
            name = pokemon.css('td.cell-name a.ent-name::text').get()
            link = pokemon.css('td.cell-name a.ent-name::attr(href)').get()
            pokemon_url = response.urljoin(link).replace('\\', '')  # Remove as barras invertidas

            types = ", ".join(pokemon.css('td.cell-icon a.type-icon::text').getall())

            yield response.follow(pokemon_url,
                                  self.parse_pokemon,
                                  meta={
                                      'number': number,
                                      'name': name,
                                      'url': pokemon_url,
                                      'types': types
                                  })

    def parse_pokemon(self, response):
        item = PokemonItem()
        item['number'] = int(response.meta['number'].lstrip('#').lstrip('0') or '0')
        item['name'] = response.meta['name']
        item['url'] = response.meta['url']
        item['types'] = response.meta['types']

        # Captura altura e peso
        item['height_cm'] = response.css('.vitals-table tr:contains("Height") td::text').get().strip()
        item['weight_kg'] = response.css('.vitals-table tr:contains("Weight") td::text').get().strip()

        # Captura evoluções
        item['next_evolutions'] = self.extract_evolutions(response, item['name'])

        # Captura habilidades
        ability_links = response.css('.vitals-table tr:contains("Abilities") td a::attr(href)').getall()
        ability_links = [response.urljoin(link).replace('\\', '') for link in ability_links]  # Remove as barras invertidas

        if ability_links:
            request = Request(ability_links[0], callback=self.parse_ability, dont_filter=True)
            request.meta['pending_abilities'] = ability_links[1:]
            request.meta['abilities'] = []
            request.meta['item'] = item
            yield request
        else:
            item['abilities'] = []
            self.items.append(dict(item))
            yield item

    def extract_evolutions(self, response, current_pokemon_name):
        evolutions = []
        current_pokemon_found = False

        for evo in response.css('.infocard-list-evo .infocard'):
            evo_number = evo.css('.text-muted small::text').get()
            evo_name = evo.css('.ent-name::text').get()
            evo_link = response.urljoin(evo.css('a::attr(href)').get()).replace('\\', '')  # Remove as barras invertidas

            if evo_name and evo_name.strip() == current_pokemon_name.strip():
                current_pokemon_found = True
            elif current_pokemon_found and evo_name and evo_number:
                evo_number_int = int(evo_number.lstrip('#').lstrip('0') or '0')
                evolutions.append({
                    'number': evo_number_int,
                    'name': evo_name,
                    'url': evo_link
                })

        return evolutions

    def parse_ability(self, response):
        ability_info = {
            'name': response.css('main > h1::text').get().strip(),
            'desc': self.clean_html_tags(response.css('.vitals-table > tbody > tr:nth-child(1) > td::text').get()),
            'effect': self.clean_html_tags(response.css('main > div > div > p').get()),
            'url': response.css('link[rel="canonical"]::attr(href)').get().replace('\\', '')  # Remove as barras invertidas
        }

        item = response.meta['item']
        abilities = response.meta['abilities']
        abilities.append(ability_info)

        pending_abilities = response.meta['pending_abilities']
        if pending_abilities:
            next_request = Request(pending_abilities[0], callback=self.parse_ability, dont_filter=True)
            next_request.meta.update(response.meta)
            next_request.meta['abilities'] = abilities
            next_request.meta['pending_abilities'] = pending_abilities[1:]
            yield next_request
        else:
            item['abilities'] = abilities
            self.items.append(dict(item))
            yield item

    def clean_html_tags(self, text):
        """Remove as tags HTML <p> e <em> e quaisquer outras tags HTML do texto."""
        if text:
            text = re.sub(r'<.*?>', '', text)  # Remove todas as tags HTML
        return text

def clean_measurement(value):
    if value:
        # Remove todos os caracteres que não são dígitos, pontos ou vírgulas
        cleaned_value = re.sub(r'[^\d.,]', '', value)
        
        # Tratar múltiplos pontos/vírgulas separando a string e mantendo a parte relevante
        if ',' in cleaned_value and '.' in cleaned_value:
            cleaned_value = cleaned_value.replace(',', '')

        # Substitui vírgulas por pontos
        cleaned_value = cleaned_value.replace(',', '.')
        
        try:
            return float(cleaned_value)
        except ValueError:
            return None  # Retorna None se não for possível converter
    return None

if __name__ == "__main__":
    process = CrawlerProcess()

    # Executa o spider
    process.crawl(PokemonScrapper)
    process.start()

    # Ordena os Pokémon por ID antes de salvar
    PokemonScrapper.items.sort(key=lambda x: x['number'])

    # Salva os resultados em um arquivo JSON
    with open('pokemons.json', 'w', encoding='utf-8') as f:
        json.dump(PokemonScrapper.items, f, ensure_ascii=False, indent=4)

    # Carrega o JSON gerado pelo Scrapy
    with open('pokemons.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Converte para DataFrame
    df = pd.DataFrame(data)

    # Remove entradas com dados nulos ou inválidos
    df.dropna(inplace=True)

    # Limpa e converte altura e peso para valores numéricos
    df['height_cm'] = df['height_cm'].apply(lambda x: clean_measurement(x) * 100 if x else None)
    df['weight_kg'] = df['weight_kg'].apply(clean_measurement)

    # Salva o DataFrame limpo em um novo arquivo JSON ou CSV
    df.to_json('pokemons_cleaned.json', orient='records', indent=4, force_ascii=False)
    df.to_csv('pokemons_cleaned.csv', index=False)
