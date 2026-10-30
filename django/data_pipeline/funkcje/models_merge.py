from pathlib import Path
import pandas as pd

# 1. Ścieżki do plików
DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent

clean_dir = DATA_PIPELINE_DIR / "clean"
models_dir = DATA_PIPELINE_DIR / "models_merge"
models_dir.mkdir(parents=True, exist_ok=True)

# dane z json
weather = pd.read_csv(clean_dir / "weather_clean.csv")
pse = pd.read_csv(clean_dir / "pse_clean.csv")

# daty
# Open-Meteo: kolumna date
# PSE: kolumna dtime

weather["date"] = pd.to_datetime(
    weather["date"], utc=True
)

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


# zapis
output_path = models_dir / "weather_pse_merged.csv"

merged.to_csv(
    output_path,
    index=False
)
print(f"Połączono {len(merged)} rekordów.")
print(f"Zapisano dane do: {output_path}")
print(merged.head())



