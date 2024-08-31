import requests

# URL da API
url = "https://weather.com/api/v1/p/redux-dal"

# Lista com coordenadas (geocode) das capitais do Brasil
capitais = {
    "Rio Branco": "-9.9754,-67.8243",
    "Maceió": "-9.6658,-35.7353",
    "Macapá": "0.0349,-51.0694",
    "Manaus": "-3.1187,-60.0212",
    "Salvador": "-12.9714,-38.5014",
    "Fortaleza": "-3.7172,-38.5434",
    "Brasília": "-15.7939,-47.8828",
    "Vitória": "-20.3155,-40.3128",
    "Goiânia": "-16.6869,-49.2648",
    "São Luís": "-2.5307,-44.3068",
    "Cuiabá": "-15.601,-56.0979",
    "Campo Grande": "-20.4697,-54.6201",
    "Belo Horizonte": "-19.9167,-43.9345",
    "Belém": "-1.4558,-48.4902",
    "João Pessoa": "-7.1195,-34.8450",
    "Curitiba": "-25.4284,-49.2733",
    "Recife": "-8.0476,-34.8770",
    "Teresina": "-5.091,-42.8034",
    "Rio de Janeiro": "-22.9068,-43.1729",
    "Natal": "-5.7945,-35.2110",
    "Porto Alegre": "-30.0346,-51.2177",
    "Porto Velho": "-8.7619,-63.9039",
    "Boa Vista": "2.8235,-60.6758",
    "Florianópolis": "-27.5954,-48.5480",
    "São Paulo": "-23.548,-46.639",
    "Aracaju": "-10.9472,-37.0731",
    "Palmas": "-10.1835,-48.3336"
}

headers = {
    "Content-Type": "application/json"
}

def extract_data(dal, config_name):
    config_data = dal.get(config_name, {})
    for key, value in config_data.items():
        if isinstance(value, dict) and 'data' in value:
            return value['data']
    return {}

dias_da_semana = {
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira",
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

def traduzir_dia(dia_em_ingles):
    return dias_da_semana.get(dia_em_ingles, dia_em_ingles)

for cidade, geocode in capitais.items():
    payload = [
        {
            "name": "getSunWeatherAlertHeadlinesUrlConfig",
            "params": {
                "geocode": geocode,
                "units": "m"
            }
        },
        {
            "name": "getSunV3CurrentObservationsUrlConfig",
            "params": {
                "geocode": geocode,
                "units": "m"
            }
        },
        {
            "name": "getSunV3DailyForecastWithHeadersUrlConfig",
            "params": {
                "duration": "7day",
                "geocode": geocode,
                "units": "m"
            }
        },
        {
            "name": "getSunIndexPollenDaypartUrlConfig",
            "params": {
                "duration": "3day",
                "geocode": geocode,
                "units": "m"
            }
        }
    ]

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        dal = data.get('dal', {})

        daily_forecast = extract_data(dal, 'getSunV3DailyForecastWithHeadersUrlConfig')
        current_observations = extract_data(dal, 'getSunV3CurrentObservationsUrlConfig')

        print(f"Dados meteorológicos para {cidade}:")

        if daily_forecast:
            calendar_day_temperature_max = daily_forecast.get('calendarDayTemperatureMax', [])
            calendar_day_temperature_min = daily_forecast.get('calendarDayTemperatureMin', [])
            day_of_week = daily_forecast.get('dayOfWeek', [])

            temperature_max = daily_forecast.get('temperatureMax', [])
            temperature_min = daily_forecast.get('temperatureMin', [])

            for i in range(len(day_of_week)):
                dia_em_portugues = traduzir_dia(day_of_week[i])
                print(f"Dia: {dia_em_portugues}")
                print(f"Temperatura Máxima Calendário: {calendar_day_temperature_max[i]}°C")
                print(f"Temperatura Mínima Calendário: {calendar_day_temperature_min[i]}°C")
                print(f"Temperatura Máxima: {temperature_max[i]}°C")
                print(f"Temperatura Mínima: {temperature_min[i]}°C")
                print("-" * 30)
        else:
            print("Não foi possível encontrar os dados de previsão diária.")

        print("=" * 50)

    except requests.exceptions.HTTPError as http_err:
        print(f"Falha na requisição para {cidade}: {response.status_code} - {response.text}")
    except Exception as err:
        print(f"Ocorreu um erro para {cidade}: {err}")