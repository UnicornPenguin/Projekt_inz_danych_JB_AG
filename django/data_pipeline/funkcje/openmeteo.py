from datetime import datetime, timezone
from pathlib import Path
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry


def fetch_and_save_raw_weather(
    latitude: float = 52.0,
    longitude: float = 20.0,
    start_date: str = "2023-01-01",
    end_date: str = "2026-10-05",
):
  """Pobieranie danych z openmeteo i raw_data do data_pipeline/raw/."""
  cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
  retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
  openmeteo = openmeteo_requests.Client(session=retry_session)

  url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
  params = {
      "latitude": latitude,
      "longitude": longitude,
      "start_date": start_date,
      "end_date": end_date,
      "hourly": ["temperature_2m", "rain", "wind_speed_10m"],
      "timezone": "auto",
  }

  print(
      f"[EXTRACT] Pobieranie danych z openmeteo dla lat={latitude},"
      f" lon={longitude}..."
  )
  responses = openmeteo.weather_api(url, params=params)
  response = responses[0]

  hourly = response.Hourly()
  hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
  hourly_rain = hourly.Variables(1).ValuesAsNumpy()
  hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()

  dates = pd.date_range(
      start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
      end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
      freq=pd.Timedelta(seconds=hourly.Interval()),
      inclusive="left",
  ).tz_convert(response.Timezone().decode())

  hourly_data = {
      "date": dates,
      "temperature_2m": hourly_temperature_2m,
      "rain": hourly_rain,
      "wind_speed_10m": hourly_wind_speed_10m,
  }

  hourly_dataframe = pd.DataFrame(data=hourly_data)


  # Plik w django/data_pipeline/funkcje/openmeteo.py
  DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent
  raw_dir = DATA_PIPELINE_DIR / "raw"
  raw_dir.mkdir(parents=True, exist_ok=True)

  timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  raw_filename = f"weather_raw_{timestamp}.json"
  raw_filepath = raw_dir / raw_filename

  hourly_dataframe.to_json(
      raw_filepath, orient="records", date_format="iso", indent=2
  )

  print(f"[EXTRACT] Zapisano surowe dane do: {raw_filepath}")
  return raw_filepath, hourly_dataframe


if __name__ == "__main__":
  sciezka, df = fetch_and_save_raw_weather()
  print("\n--- Podgląd pierwszych 5 wierszy ---")
  print(df.head())