from datetime import datetime, timedelta
import pandas as pd
import requests_cache
from retry_requests import retry

# 1. Konfiguracja sesji
cache_session = requests_cache.CachedSession('.cache_pse', expire_after=1800)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)

# 2. Zakres dat (dzisiaj i wczoraj)
today = datetime.now().strftime('%Y-%m-%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# 3. Działający endpoint API PSE (Rynkowa Cena Energii)
endpoint = "rce-pln"
url = f"https://api.raporty.pse.pl/api/{endpoint}"

params = {
    "$filter": f"business_date ge '{yesterday}' and business_date le '{today}'",
    "$first": 500
}

print(f"Pobieranie danych z API PSE ({endpoint})...")

try:
    response = retry_session.get(url, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()

    records = payload.get("value", [])

    if records:
        df = pd.DataFrame(records)
        print(f"\n SUKCES! Pobrano {len(df)} rekordów.\n")
        
        # Wyświetlenie nazw dostępnych kolumn
        print("Dostępne kolumny w tym raporcie:")
        print(df.columns.tolist())
        print("\nPierwsze 5 wierszy:")
        print(df.head())
    else:
        print("Zapytanie zwróciło pustą listę (brak danych).")

except Exception as e:
    print(f" Błąd połączenia lub zapytania: {e}")