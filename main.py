import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request
import json
import pandas as pd
import re
import time

class PokemonItem(scrapy.Item):
    numero = scrapy.Field()
    nome = scrapy.Field()
    url = scrapy.Field()
    tipos = scrapy.Field()
    altura_cm = scrapy.Field()
    peso_kg = scrapy.Field()
    proximas_evolucoes = scrapy.Field()
    habilidades = scrapy.Field()

class PokemonScraper(scrapy.Spider):
    name = 'pokemon_scraper'
    start_urls = ["https://pokemondb.net/pokedex/all"]
    itens = []

    def __init__(self):
        self.processed_pokemon_urls = set()  # Usado para rastrear URLs já processadas

    def parse(self, response):
        pokemons = response.css('#pokedex tbody tr')
        for pokemon in pokemons:
            numero = self.parse_numero(pokemon)
            nome = self.parse_nome(pokemon)
            pokemon_url = self.parse_url(pokemon, response)
            tipos = ", ".join(pokemon.css('td.cell-icon a.type-icon::text').getall())

            if numero and nome and pokemon_url:
                if pokemon_url not in self.processed_pokemon_urls:
                    self.processed_pokemon_urls.add(pokemon_url)
                    self.log(f"Capturando Pokémon: {numero} - {nome}")
                    yield response.follow(pokemon_url,
                                          self.parse_pokemon,
                                          meta={
                                              'numero': numero,
                                              'nome': nome,
                                              'url': pokemon_url,
                                              'tipos': tipos
                                          })
                    #time.sleep(1)  # Adiciona um pequeno delay entre requests para evitar bloqueios

    def parse_numero(self, pokemon):
        return pokemon.css('td.cell-num span.infocard-cell-data::text').get()

    def parse_nome(self, pokemon):
        return pokemon.css('td.cell-name a.ent-name::text').get()

    def parse_url(self, pokemon, response):
        link = pokemon.css('td.cell-name a.ent-name::attr(href)').get()
        return response.urljoin(link)

    def parse_pokemon(self, response):
        item = self.create_pokemon_item(response)
        evolucoes = self.parse_evolucoes(response, item)
        item['proximas_evolucoes'] = evolucoes

        links_habilidades = response.css('.vitals-table tr:contains("Abilities") td a::attr(href)').getall()
        links_habilidades = [response.urljoin(link) for link in links_habilidades]

        if links_habilidades:
            request = Request(links_habilidades[0], callback=self.parse_habilidade, dont_filter=True)
            request.meta['habilidades_pendentes'] = links_habilidades[1:]
            request.meta['habilidades'] = []
            request.meta['item'] = item
            yield request
        else:
            item['habilidades'] = []
            self.save_item(item)
            yield item

    def create_pokemon_item(self, response):
        item = PokemonItem()
        item['numero'] = int(response.meta['numero'].lstrip('#').lstrip('0') or '0')
        item['nome'] = response.meta['nome']
        item['url'] = response.meta['url']
        item['tipos'] = response.meta['tipos']
        item['altura_cm'] = response.css('.vitals-table tr:contains("Height") td::text').get().strip()
        item['peso_kg'] = response.css('.vitals-table tr:contains("Weight") td::text').get().strip()
        return item

    def parse_evolucoes(self, response, item):
        evolucoes = []
        pokemon_atual_encontrado = False
        for evo in response.css('.infocard-list-evo .infocard'):
            numero_evo = evo.css('.text-muted small::text').get()
            nome_evo = evo.css('.ent-name::text').get()
            link_evo = response.urljoin(evo.css('a::attr(href)').get())

            if nome_evo and nome_evo.strip() == item['nome'].strip():
                pokemon_atual_encontrado = True
            elif pokemon_atual_encontrado and nome_evo and numero_evo:
                numero_evo_int = int(numero_evo.lstrip('#').lstrip('0') or '0')
                evolucoes.append({
                    'numero': numero_evo_int,
                    'nome': nome_evo,
                    'url': link_evo
                })
        return evolucoes

    def parse_habilidade(self, response):
        habilidade = self.extract_habilidade(response)

        item = response.meta['item']
        habilidades = response.meta['habilidades']
        habilidades.append(habilidade)

        habilidades_pendentes = response.meta['habilidades_pendentes']
        if habilidades_pendentes:
            proxima_requisicao = Request(habilidades_pendentes[0], callback=self.parse_habilidade, dont_filter=True)
            proxima_requisicao.meta.update(response.meta)
            proxima_requisicao.meta['habilidades'] = habilidades
            proxima_requisicao.meta['habilidades_pendentes'] = habilidades_pendentes[1:]
            yield proxima_requisicao
        else:
            item['habilidades'] = habilidades
            self.save_item(item)
            yield item

    def extract_habilidade(self, response):
        return {
            'nome': response.css('main > h1::text').get().strip(),
            'desc': response.css('.vitals-table > tbody > tr:nth-child(1) > td::text').get(),
            'efeito': response.css('main > div > div > p').get(),
            'url': response.css('link[rel="canonical"]::attr(href)').get()
        }

    def save_item(self, item):
        self.itens.append(dict(item))

    def closed(self, reason):
        # Ordena a lista de pokémons pelo número
        sorted_pokemons = sorted(self.itens, key=lambda x: x['numero'])

        # Salva os pokémons ordenados em um arquivo JSON
        with open('pokemons_sorted.json', 'w', encoding='utf-8') as f:
            json.dump(sorted_pokemons, f, ensure_ascii=False, indent=4)

        # Log para indicar que o arquivo foi salvo
        self.log("Arquivo JSON salvo com sucesso.")

        # Processa e limpa os dados usando pandas
        df = pd.DataFrame(sorted_pokemons)
        df.dropna(inplace=True)

        df['altura_cm'] = df['altura_cm'].apply(lambda x: limpar_medida(x) * 100 if x else None)
        df['peso_kg'] = df['peso_kg'].apply(limpar_medida)

        df.to_json('pokemons_limpos.json', orient='records', indent=4, force_ascii=False)
        df.to_csv('pokemons_limpos.csv', index=False)

def limpar_medida(valor):
    if valor:
        valor_limpo = re.sub(r'[^\d.,]', '', valor)
        partes = re.findall(r'\d+', valor_limpo)
        if len(partes) > 1:
            valor_limpo = '.'.join(partes[-2:])
        else:
            valor_limpo = partes[0]
        valor_limpo = valor_limpo.replace(',', '.')
        try:
            return float(valor_limpo)
        except ValueError:
            return None
    return None

if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(PokemonScraper)
    process.start()
