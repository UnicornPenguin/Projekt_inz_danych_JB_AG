from datetime import datetime, timezone
from pathlib import Path
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

def fetch_and_save_raw_weather(
    latitude: float = 52.52,
    longitude: float = 13.41,
    start_date: str = "2024-06-14",
    end_date: str = "2026-10-05",
):
    """Pobieranie danych co 15 minut z Open-Meteo i zapis do raw."""

    # 1. Konfiguracja sesji
    cache_session = requests_cache.CachedSession(
        ".cache", expire_after=3600
    )
    retry_session = retry(
        cache_session, retries=5, backoff_factor=0.2
    )
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # 2. Parametry API
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"

    variables = [
        "temperature_2m",
        "wind_speed_10m",
        "rain",
        "snowfall",
        "sunshine_duration",
        "is_day",
        "apparent_temperature",
        "snowfall_height",
    ]

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "minutely_15": variables,
        "timezone": "Europe/Warsaw",
    }

    print(
        f"[EXTRACT] Pobieranie danych Open-Meteo "
        f"od {start_date} do {end_date}..."
    )

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    # 3. Odczyt danych 15-minutowych
    minutely_15 = response.Minutely15()

    dates = pd.date_range(
        start=pd.to_datetime(
            minutely_15.Time(), unit="s", utc=True
        ),
        end=pd.to_datetime(
            minutely_15.TimeEnd(), unit="s", utc=True
        ),
        freq=pd.Timedelta(
            seconds=minutely_15.Interval()
        ),
        inclusive="left",
    ).tz_convert("Europe/Warsaw")

    # 4. Utworzenie DataFrame
    minutely_15_data = {"date": dates}

    for i, variable in enumerate(variables):
        minutely_15_data[variable] = (
            minutely_15.Variables(i).ValuesAsNumpy()
        )

    minutely_15_dataframe = pd.DataFrame(
        data=minutely_15_data
    )

    print(
        f"[EXTRACT] Pobrano "
        f"{len(minutely_15_dataframe)} rekordów."
    )

    # 5. Utworzenie folderu RAW
    DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent

    raw_dir = DATA_PIPELINE_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 6. Nazwa pliku
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    raw_filename = f"weather_raw.json"
    raw_filepath = raw_dir / raw_filename

    # 7. Zapis danych do JSON
    minutely_15_dataframe.to_json(
        raw_filepath,
        orient="records",
        date_format="iso",
        date_unit="s",
        indent=2,
        force_ascii=False,
    )

    print(
        f"[EXTRACT] Zapisano dane RAW do: {raw_filepath}"
    )

    return raw_filepath, minutely_15_dataframe


if __name__ == "__main__":
    sciezka, df = fetch_and_save_raw_weather()

    print("\n--- Pierwsze 5 wierszy ---")
    print(df.head())

    print("\n--- Ostatnie 5 wierszy ---")
    print(df.tail())
