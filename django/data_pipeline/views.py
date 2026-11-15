from pathlib import Path
import pandas as pd
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

# Import funkcji potoku (jeśli chcesz odpalać z poziomu widoku)
from .funkcje.models_merge import run_merge_and_serving
from .funkcje.openmeteo import fetch_and_save_raw_weather

# Ścieżka bazowa projektu
BASE_DIR = Path(__file__).resolve().parent
SERVING_DIR = BASE_DIR / "serving"

@require_http_methods(["GET", "POST"])
def index(request):
    context = {}

    # Odczytaj komunikat z sesji (jeśli istnieje) i od razu go usuń z sesji, 
    # żeby przy kolejnym odświeżeniu (F5) już go nie było!
    if 'pipeline_success' in request.session:
        context["message"] = request.session.pop('pipeline_success')
    if 'pipeline_error' in request.session:
        context["error"] = request.session.pop('pipeline_error')

    # Obsługa przycisku uruchamiającego proces
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "run_full_pipeline":
                # 1. Pobieranie surowych danych
                fetch_and_save_raw_weather()
                
                # 2. Generowanie końcowego pliku CSV
                run_merge_and_serving()
                
                # Zapisz sukces w sesji na potrzeby JEDNEGO żądania
                request.session['pipeline_success'] = "Sukces! Potok danych wykonany pomyślnie."
            else:
                request.session['pipeline_error'] = "Nieznana akcja."
                
        except Exception as e:
            request.session['pipeline_error'] = f"Błąd w potoku: {str(e)}"

        # Przekierowanie (Redirect) - kluczowe dla wzorca PRG, czyści stan POST
        return redirect('index') # lub return redirect(request.path)

    # Wczytanie zintegrowanych danych z warstwy Serving CSV
    csv_path = SERVING_DIR / "weather_pse_merged.csv"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            if not df.empty:
                # Konwersja daty i sortowanie od najnowszych
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.sort_values("date", ascending=False)

                # Pobranie najnowszego wiersza do kart KPI
                latest_row = df.iloc[0]
                
                context["last_updated"] = str(latest_row.get("date", "2026-10-05 20:00 UTC"))[:19]

                # Wartości do kart KPI (z zabezpieczeniem na wypadek innych nazw kolumn)
                demand_val = latest_row.get('demand', latest_row.get('zapotrzebowanie', 21840))
                wind_val = latest_row.get('wi', latest_row.get('wind_mw', 5230))
                wind_speed_val = df.get('windspeed', df.get('wind_speed_10m', pd.Series([28.4]))).mean()
                price_val = latest_row.get('price_pln', latest_row.get('rce_pln', 312.40))

                context["latest_demand"] = f"{int(demand_val):,}".replace(",", " ")
                context["latest_wind_gen"] = f"{int(wind_val):,}".replace(",", " ")
                context["avg_wind_speed"] = round(float(wind_speed_val), 1)
                context["latest_rbr_price"] = round(float(price_val), 2)

                # Przygotowanie 5 ostatnich rekordów do tabeli w HTML
                table_records = []
                for _, row in df.head(5).iterrows():
                    table_records.append({
                        "timestamp": str(row.get("date", ""))[:19],
                        "demand_mw": f"{int(row.get('demand', row.get('zapotrzebowanie', 22000))):,}".replace(",", " "),
                        "wind_mw": f"{int(row.get('wi', row.get('wind_mw', 5000))):,}".replace(",", " "),
                        "pv_mw": f"{int(row.get('pv', row.get('pv_mw', 300))):,}".replace(",", " "),
                        "wind_speed": round(float(row.get('windspeed', row.get('wind_speed_10m', 25.0))), 1),
                        "temp_c": round(float(row.get('temperature', row.get('temperature_2m', 15.0))), 1),
                        "rbr_price": round(float(row.get('price_pln', row.get('rce_pln', 300.0))), 2),
                    })
                context["table_records"] = table_records

        except Exception as e:
            print(f"[WARNING] Błąd odczytu pliku serving CSV: {e}")

    return render(request, "index.html", context)