"""Analizy pogody i RCE wyłącznie na podstawie serving/weather_pse_merged.csv.

Jednostka analizy: godzina UTC. Dane RCE z przedziałów 15-minutowych
są uśredniane do godzin, dzięki czemu nie mnożymy sztucznie obserwacji
pogodowych. Dane pogodowe mogą opisywać tylko lokalizację z Open-Meteo,
a nie całą Polskę.
"""
from __future__ import annotations

import math
import pandas as pd

COLS = {
    'time': ('dtime_utc', 'date', 'timestamp', 'pse_time'),
    'temperature': ('temperature', 'temperature_2m', 'temp_c'),
    'windspeed': ('windspeed', 'wind_speed_10m', 'wind_speed'),
    'sunshine': ('sunshine', 'sunshine_duration'),
    'price': ('price_pln', 'rce_pln'),
    'rain': ('rain',),
    'snowfall': ('snowfall',),
}


def _column(df, key):
    return next((c for c in COLS[key] if c in df.columns), None)


def _num(v, places=2):
    if v is None or pd.isna(v) or not math.isfinite(float(v)):
        return None
    return round(float(v), places)


def _stats(x):
    x = pd.to_numeric(x, errors='coerce').dropna()
    return {'count': int(len(x)), 'mean': _num(x.mean()),
            'median': _num(x.median()), 'std': _num(x.std()) if len(x) > 1 else None}


def _correlation(x, y):
    valid = pd.DataFrame({'x': x, 'y': y}).dropna()
    if len(valid) < 10 or valid.x.nunique() < 3 or valid.y.nunique() < 3:
        return None, len(valid)
    return _num(valid.x.corr(valid.y), 3), len(valid)


def _serialize(d):
    return [{'x': _num(r[0]), 'y': _num(r[1])} for r in d.itertuples(index=False, name=None)
            if pd.notna(r[0]) and pd.notna(r[1])]


def build_dashboard(raw):
    if raw.empty:
        return {'data_warning': 'CSV jest pusty.'}

    required = ('time', 'price', 'temperature', 'windspeed', 'sunshine')
    missing = [k for k in required if _column(raw, k) is None]
    if missing:
        return {'data_warning': 'W CSV brakuje kolumn: ' + ', '.join(missing)}

    df = pd.DataFrame(index=raw.index)
    # dtime_utc to czas rozpoczęcia przedziału RCE, bez przesunięć czasu lokalnego.
    df['time'] = pd.to_datetime(raw[_column(raw, 'time')], utc=True, errors='coerce')
    for key in ('price', 'temperature', 'windspeed', 'sunshine'):
        df[key] = pd.to_numeric(raw[_column(raw, key)], errors='coerce')
    df = df.dropna(subset=['time'])
    if df.empty:
        return {'data_warning': 'Nie można rozpoznać dat w CSV.'}

    # Jeden wiersz na godzinę. Ceny: średnia 15-minutowych RCE; pogoda: pierwszy
    # niepusty odczyt w obrębie godziny, ponieważ zwykle został powielony przez merge.
    df['hour'] = df.time.dt.floor('h')
    def first_valid(s):
        s = s.dropna()
        return s.iloc[0] if len(s) else float('nan')

    hourly = (df.groupby('hour', sort=True)
              .agg(price=('price', 'mean'), temperature=('temperature', first_valid),
                   windspeed=('windspeed', first_valid), sunshine=('sunshine', first_valid),
                   price_samples=('price', 'count'))
              .reset_index())
    valid = hourly.dropna(subset=['price'])
    if valid.empty:
        return {'data_warning': 'W CSV nie ma poprawnych cen RCE.'}

    last = valid.iloc[-1]
    beginning, ending = hourly.hour.min(), hourly.hour.max()
    result = {
        'source_file': 'weather_pse_merged.csv',
        'last_updated': ending.strftime('%Y-%m-%d %H:%M UTC'),
        'first_updated': beginning.strftime('%Y-%m-%d %H:%M UTC'),
        'raw_rows': len(raw), 'hourly_rows': len(hourly),
        'latest_price': _num(last.price),
        'latest_temp': _num(last.temperature, 1),
        'latest_wind': _num(last.windspeed, 1),
        'latest_sunshine': _num(last.sunshine, 1),
        'price_summary': _stats(valid.price),
        'data_warning': None,
        'method_note': 'Cena: średnia z dostępnych obserwacji 15-minutowych w godzinie UTC; pogoda: pojedynczy odczyt godzinowy. Zależności statystyczne nie dowodzą przyczynowości.',
    }

    # P1: Temperatura i RCE. Kategorie a priori, bez wniosków o zapotrzebowaniu.
    temp_df = hourly.dropna(subset=['temperature', 'price']).copy()
    breaks = [-float('inf'), 0, 15, 25, float('inf')]
    labels = ['< 0°C', '0–15°C', '15–25°C', '> 25°C']
    temp_df['band'] = pd.cut(temp_df.temperature, bins=breaks, labels=labels, right=False)
    # Powyżej 25°C włącznie nie jest w tej analizie celem — warunek >25.
    temp_df.loc[temp_df.temperature == 25, 'band'] = '15–25°C'
    temp_groups = []
    for label in labels:
        s = temp_df.loc[temp_df.band == label, 'price']
        temp_groups.append({'label': label, **_stats(s)})
    result['temperature_bands'] = temp_groups
    result['temp_corr'], result['temp_n'] = _correlation(temp_df.temperature, temp_df.price)
    result['temp_scatter'] = _serialize(temp_df[['temperature', 'price']].sample(
        min(800, len(temp_df)), random_state=42))

    # P2: siła wiatru oraz zmienność ceny w grupach (odchylenie standardowe).
    wind_df = hourly.dropna(subset=['windspeed', 'price']).copy()
    result['wind_corr'], result['wind_n'] = _correlation(wind_df.windspeed, wind_df.price)
    wind_df['band'] = pd.cut(wind_df.windspeed, bins=[-float('inf'), 10, 25, float('inf')],
                              labels=['< 10 km/h', '10–25 km/h', '≥ 25 km/h'], right=False)
    result['wind_bands'] = [
        {'label': lab, **_stats(wind_df.loc[wind_df.band == lab, 'price'])}
        for lab in ['< 10 km/h', '10–25 km/h', '≥ 25 km/h']
    ]
    result['wind_scatter'] = _serialize(wind_df[['windspeed', 'price']].sample(
        min(800, len(wind_df)), random_state=42))

    # P3: usłonecznienie > 0 vs 0, wyłącznie w godzinach 07:00–17:59 UTC.
    # Jest to prosta analiza opisowa, nie porównanie natężenia promieniowania.
    sun_df = hourly.dropna(subset=['sunshine', 'price']).copy()
    sun_df = sun_df[(sun_df.hour.dt.hour >= 7) & (sun_df.hour.dt.hour < 18)]
    result['sun_groups'] = [
        {'label': 'Bez usłonecznienia (0)', **_stats(sun_df.loc[sun_df.sunshine == 0, 'price'])},
        {'label': 'Z usłonecznieniem (>0)', **_stats(sun_df.loc[sun_df.sunshine > 0, 'price'])},
    ]
    result['sun_corr'], result['sun_n'] = _correlation(sun_df.sunshine, sun_df.price)
    result['sun_unit_note'] = 'Kolumna sunshine; przed interpretacją jednostek sprawdź konfigurację zapytania Open-Meteo.'

    # P4: dobowy profil ceny i zmienność dla każdej godziny UTC.
    hourly['hour_of_day'] = hourly.hour.dt.hour
    profile = hourly.groupby('hour_of_day').price.agg(['mean', 'median', 'std', 'count'])
    result['day_profile'] = [
        {'hour': f'{h:02d}:00', 'mean': _num(profile.loc[h, 'mean']) if h in profile.index else None,
         'median': _num(profile.loc[h, 'median']) if h in profile.index else None,
         'std': _num(profile.loc[h, 'std']) if h in profile.index else None,
         'count': int(profile.loc[h, 'count']) if h in profile.index else 0}
        for h in range(24)
    ]
    recent = hourly.tail(168)
    result['timeline'] = {
        'labels': [t.strftime('%d.%m %H:%M') for t in recent.hour],
        'price': [_num(v) for v in recent.price],
        'temperature': [_num(v, 1) for v in recent.temperature],
        'windspeed': [_num(v, 1) for v in recent.windspeed],
    }
    result['table_records'] = [
        {'time': r.hour.strftime('%Y-%m-%d %H:%M UTC'),
         'temperature': _num(r.temperature, 1), 'windspeed': _num(r.windspeed, 1),
         'sunshine': _num(r.sunshine, 1), 'price': _num(r.price)}
        for r in hourly.tail(10).iloc[::-1].itertuples(index=False)
    ]
    return result