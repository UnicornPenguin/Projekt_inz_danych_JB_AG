from pathlib import Path
import pandas as pd

#utworzenie sciezki do plikow

DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent #zmienna niezmienna

raw_dir = DATA_PIPELINE_DIR / "raw"
clean_dir = DATA_PIPELINE_DIR / "clean"

clean_dir.mkdir(parents=True, exist_ok=True)

weather = pd.read_json(raw_dir / "weather_raw.json") #dane z json

pse = pd.read_json(raw_dir / "pse_raw.json") #dane z json

def clean_data(weather, pse):

    if "date" not in weather.columns:
        raise ValueError("Brak kolumny date w weather.")

    if "dtime" not in pse.columns:
        raise ValueError(
            f"Brak kolumny dtime w PSE. Dostępne: {pse.columns.tolist()}"
        )

    if "rce_pln" not in pse.columns:
        raise ValueError("Brak kolumny rce_pln w PSE.")

    weather["date"] = pd.to_datetime(
        weather["date"], utc=True, errors="coerce"
    )

    pse["date"] = pd.to_datetime(
        pse["dtime"], utc=True, errors="coerce"
    )

    weather = weather.dropna(subset=["date"])
    pse = pse.dropna(subset=["date"])

    weather_columns = weather.columns.drop(["date"])

    for column in weather_columns:
        weather[column] = pd.to_numeric(
            weather[column], errors="coerce"
        )

    pse["rce_pln"] = pd.to_numeric(
        pse["rce_pln"], errors="coerce"
    )

    weather = ( #usuwanie duplikatów
        weather.drop_duplicates(subset=["date"])
        .sort_values(by="date")
        .reset_index(drop=True)
    )
    pse = (
        pse.drop_duplicates(subset=["date"])
        .sort_values(by="date")
        .reset_index(drop=True)
    )

    pse = pse.dropna(subset=["rce_pln"])

    return weather, pse

weather.to_csv(clean_dir / "weather_clean.csv", index=False)
pse.to_csv(clean_dir / "pse_clean.csv", index=False)

print(f"[CLEAN] Zapisano dane do: {clean_dir / 'weather_clean.csv'}")
print(f"[CLEAN] Zapisano dane do: {clean_dir / 'pse_clean.csv'}")
print(f"[CLEAN] Zapisano dane do folderu clean: {clean_dir}")

if __name__ == "__main__":
    weather, pse = clean_data(weather, pse)

    print("\n_WEATHER_")
    print(weather.head())
    print("\n_PSE_")
    print(pse.head())