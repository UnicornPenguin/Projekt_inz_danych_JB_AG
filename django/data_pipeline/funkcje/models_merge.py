from pathlib import Path
import pandas as pd

def run_merge_and_serving():
    # 1. Ścieżki do plików
    DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent

    clean_dir = DATA_PIPELINE_DIR / "clean"
    models_dir = DATA_PIPELINE_DIR / "models_merge"
    serving_dir = DATA_PIPELINE_DIR / "serving"

    models_dir.mkdir(parents=True, exist_ok=True)
    serving_dir.mkdir(parents=True, exist_ok=True)

    # 2. Wczytywanie oczyszczonych danych
    weather = pd.read_csv(clean_dir / "weather_clean.csv")
    pse = pd.read_csv(clean_dir / "pse_clean.csv")

    # daty
    # Open-Meteo: kolumna date
    # PSE: kolumna dtime

    # 3. Konwersja dat
    weather["date"] = pd.to_datetime(weather["date"], utc=True)

    if "dtime_utc" in pse.columns:
        pse["date"] = pd.to_datetime(
            pse["dtime_utc"],
            utc=True,
            format="mixed"
        )
    else:
        raise ValueError(
            "Brak kolumny dtime_utc. Sprawdź dostępne kolumny PSE."
        )

    # 4. Ujednolicenie czasu do 15 minut
    weather["date"] = weather["date"].dt.floor("15min")
    pse["date"] = pse["date"].dt.floor("15min")

    # 5. INNER JOIN
    merged = pd.merge( #łączenie danych pokrywających się w tabele
        weather,
        pse,
        on="date",
        how="inner"
    )

    merged = merged.rename(columns=
        {
            "rce_pln": "price_pln",
            "temperature_2m": "temperature",
            "wind_speed_10m": "windspeed",
            "sunshine_duration": "sunshine",
            "is_day": "day_night", #where 1 = day, 0 = night
            "dtime": "pse_time"
        }
    )

    merged = merged.drop(
        columns=["snowfall_height"],
        errors="ignore"
        )

# 6. Dodatkowe czyszczenie i zmiana formatów pod Serving
    merged = merged.drop_duplicates(subset=["date"])
    merged = merged.dropna().sort_values("date").reset_index(drop=True)

    # Konwersja typów i zaokrąglenie wartości numerycznych
    if "day_night" in merged.columns:
        merged["day_night"] = merged["day_night"].astype(int)
        
    numeric_cols = merged.select_dtypes(include=["float64", "float32"]).columns
    merged[numeric_cols] = merged[numeric_cols].round(2)

    # Formatowanie daty na czytelny string (YYYY-MM-DD HH:MM:SS)
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 7. Zapis do models_merge oraz do serving w formacie CSV
    output_models_path = models_dir / "weather_pse_merged.csv"
    output_serving_path = serving_dir / "weather_pse_merged.csv"

    merged.to_csv(output_models_path, index=False)
    merged.to_csv(output_serving_path, index=False)

    print(f"Połączono i oczyszczono {len(merged)} rekordów.")
    print(f"Zapisano dane do serving: {output_serving_path}")
    print(merged.head())
    
    return output_serving_path, merged

if __name__ == "__main__":
    run_merge_and_serving()