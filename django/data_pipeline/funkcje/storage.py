# import openmeteo_requests
# import pandas as pd
# import requests_cache
# from retry_requests import retry


# def fetch_weather_raw(
#     latitude: float = 52.0,
#     longitude: float = 20.0,
#     start_date: str = "2023-01-01",
#     end_date: str = "2024-12-31",
# ) -> dict:
#     """Pobiera dane z API Open-Meteo i zwraca je w postaci słownika gotowego do zapisu w JSON."""
#     cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
#     retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
#     openmeteo = openmeteo_requests.Client(session=retry_session)

#     url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
#     params = {
#         "latitude": latitude,
#         "longitude": longitude,
#         "start_date": start_date,
#         "end_date": end_date,
#         "hourly": ["temperature_2m", "rain", "wind_speed_10m"],
#         "timezone": "auto",
#     }

#     responses = openmeteo.weather_api(url, params=params)
#     response = responses[0]

#     hourly = response.Hourly()

#     # Wyciągamy tablice z API i konwertujemy do zwykłych list w Pythonie (dla kompatybilności z json.dump)
#     temps = hourly.Variables(0).ValuesAsNumpy().tolist()
#     rains = hourly.Variables(1).ValuesAsNumpy().tolist()
#     winds = hourly.Variables(2).ValuesAsNumpy().tolist()

#     # Generujemy listę dat w formacie ISO (string)
#     dates = (
#         pd.date_range(
#             start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
#             end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
#             freq=pd.Timedelta(seconds=hourly.Interval()),
#             inclusive="left",
#         )
#         .tz_convert(response.Timezone().decode())
#         .strftime("%Y-%m-%d %H:%M:%S")
#         .tolist()
#     )

#     # Przygotowujemy czysty słownik metadanych i odczytów surowych
#     raw_payload = {
#         "metadata": {
#             "latitude": float(response.Latitude()),
#             "longitude": float(response.Longitude()),
#             "elevation": float(response.Elevation()),
#             "timezone": response.Timezone().decode(),
#             "timezone_abbreviation": response.TimezoneAbbreviation().decode(),
#             "utc_offset_seconds": int(response.UtcOffsetSeconds()),
#         },
#         "hourly": {
#             "date": dates,
#             "temperature_2m": temps,
#             "rain": rains,
#             "wind_speed_10m": winds,
#         },
#     }

#     return raw_payload