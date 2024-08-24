import requests

# URL da API
url = "https://weather.com/api/v1/p/redux-dal"

payload = [
    {
        "name": "getSunWeatherAlertHeadlinesUrlConfig",
        "params": {
            "geocode": "-23.548,-46.639",
            "units": "m"
        }
    },
    {
        "name": "getSunV3CurrentObservationsUrlConfig",
        "params": {
            "geocode": "-23.548,-46.639",
            "units": "m"
        }
    },
    {
        "name": "getSunV3DailyForecastWithHeadersUrlConfig",
        "params": {
            "duration": "7day",
            "geocode": "-23.548,-46.639",
            "units": "m"
        }
    },
    {
        "name": "getSunIndexPollenDaypartUrlConfig",
        "params": {
            "duration": "3day",
            "geocode": "-23.548,-46.639",
            "units": "m"
        }
    }
]

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    dal = data.get('dal', {})
    def extract_data(config_name):
        config_data = dal.get(config_name, {})
        for key, value in config_data.items():
            if isinstance(value, dict) and 'data' in value:
                return value['data']
        return {}


    daily_forecast = extract_data('getSunV3DailyForecastWithHeadersUrlConfig')
    current_observations = extract_data('getSunV3CurrentObservationsUrlConfig')

    if daily_forecast:
        calendar_day_temperature_max = daily_forecast.get('calendarDayTemperatureMax', [])
        calendar_day_temperature_min = daily_forecast.get('calendarDayTemperatureMin', [])
        day_of_week = daily_forecast.get('dayOfWeek', [])

        temperature_max = daily_forecast.get('temperatureMax', [])
        temperature_min = daily_forecast.get('temperatureMin', [])

        for i in range(len(day_of_week)):
            print(f"Dia: {day_of_week[i]}")
            print(f"Temperatura Máxima Calendário: {calendar_day_temperature_max[i]}°C")
            print(f"Temperatura Mínima Calendário: {calendar_day_temperature_min[i]}°C")
            print(f"Temperatura Máxima: {temperature_max[i]}°C")
            print(f"Temperatura Mínima: {temperature_min[i]}°C")
            print("-" * 30)
    else:
        print("Não foi possível encontrar os dados de previsão diária.")

except requests.exceptions.HTTPError as http_err:
    print(f"Falha na requisição: {response.status_code} - {response.text}")
except Exception as err:
    print(f"Ocorreu um erro: {err}")
