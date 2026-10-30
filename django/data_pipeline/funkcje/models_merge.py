# from pathlib import Path
# import pandas as pd

# # 1. Ścieżki do plików
# DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent

# raw_dir = DATA_PIPELINE_DIR / "raw"
# models_dir = DATA_PIPELINE_DIR / "models_merge"
# models_dir.mkdir(parents=True, exist_ok=True)

# # dane z json
# weather = pd.read_json(raw_dir / "weather_raw.json")
# pse = pd.read_json(raw_dir / "pse_raw.json")

# # daty
# # Open-Meteo: kolumna date
# # PSE: kolumna dtime

# weather["date"] = pd.to_datetime(
#     weather["date"], utc=True
# )

# if "dtime_utc" in pse.columns:
#     pse["date"] = pd.to_datetime(
#         pse["dtime_utc"],
#         utc=True,
#         format="mixed"
#     )
# else:
#     raise ValueError(
#         "Brak kolumny dtime_utc. Sprawdź dostępne kolumny PSE."
#     )

# # 4. Ujednolicenie czasu do 15 minut
# weather["date"] = weather["date"].dt.floor("15min")
# pse["date"] = pse["date"].dt.floor("15min")

# # 5. INNER JOIN
# merged = pd.merge( #łączenie danych pokrywających się w tabele
#     weather,
#     pse,
#     on="date",
#     how="inner"
# )

# # 6. Zapis wyniku
# output_path = models_dir / "weather_pse.json"

# merged.to_json(
#     output_path,
#     orient="records",
#     date_format="iso",
#     indent=2,
#     force_ascii=False
# )

# print(f"Połączono {len(merged)} rekordów.")
# print(f"Zapisano dane do: {output_path}")
# print(merged.head())

