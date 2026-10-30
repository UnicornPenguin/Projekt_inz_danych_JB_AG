from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests_cache
from retry_requests import retry
from urllib.parse import quote

# 1. Konfiguracja sesji
cache_session = requests_cache.CachedSession('.cache_pse', expire_after=1800)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)

# 2. Zakres dat (dzisiaj i wczoraj)
# today = "2023-02-01"
# yesterday = "2023-01-01"

start_date = "2024-06-14"
end_date = "2026-10-05"

# 3. Działający endpoint API PSE (Rynkowa Cena Energii)
endpoint = "rce-pln"
# endpoint = "ogr-oper"

filter_text = (
    f"business_date ge '{start_date}' "
    f"and business_date le '{end_date}'"
)

encoded_filter = quote(filter_text, safe="'")

url = (
    f"https://api.raporty.pse.pl/api/{endpoint}"
     f"?$filter={encoded_filter}&$first=500"
)

# params = {
#     "from_dtime": yesterday,
#     "to_dtime": today,
# }

print(f"Pobieranie danych z API PSE ({endpoint})...")

all_records = []
page = 1

try:
    while url:
        response = retry_session.get(url, timeout=60)
        response.raise_for_status()

        payload = response.json()
        records = payload.get("value", [])

        all_records.extend(records)

        print(f"Strona {page}: pobrano {len(records)} rekordów")
        print(f"Łącznie: {len(all_records)} rekordów")

        # Przejście do kolejnych 500 rekordów
        next_link = payload.get("nextLink")

        if next_link:
            from urllib.parse import urljoin
            url = urljoin(response.url, next_link)
        else:
            break

        page += 1

    df = pd.DataFrame(all_records)

    print(f"\nSUKCES! Pobrano łącznie {len(df)} rekordów.")
    print(df.head())

except Exception as e:
    print(f"Błąd: {e}")


DATA_PIPELINE_DIR = Path(__file__).resolve().parent.parent
raw_dir = DATA_PIPELINE_DIR / "raw"
raw_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
raw_filename = f"pse_raw.json"
raw_filepath = raw_dir / raw_filename

df.to_json(
    raw_filepath, orient="records", date_format="iso", indent=2
)

print(f"[EXTRACT] Zapisano surowe dane do: {raw_filepath}")



# curl -X 'GET' \
#   'https://api.raporty.pse.pl/api/rce-pln' \
#   -H 'accept: application/json'