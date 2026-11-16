from pathlib import Path
import logging
import pandas as pd
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .funkcje.models_merge import run_merge_and_serving
from .funkcje.openmeteo import fetch_and_save_raw_weather
from .dashboard_analytics import build_dashboard

logger = logging.getLogger(__name__)
SERVING_PATH = Path(__file__).resolve().parent / 'serving' / 'weather_pse_merged.csv'


@require_http_methods(['GET', 'POST'])
def index(request):
    # Dotychczasowa obsługa przycisku pozostaje niezmieniona.
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'run_full_pipeline':
                fetch_and_save_raw_weather()
                run_merge_and_serving()
                request.session['pipeline_success'] = 'Sukces! Potok danych wykonany pomyślnie.'
            else:
                request.session['pipeline_error'] = 'Nieznana akcja.'
        except Exception as exc:
            logger.exception('Błąd uruchamiania pipeline')
            request.session['pipeline_error'] = f'Błąd w potoku: {exc}'
        return redirect('index')

    context = {}
    if 'pipeline_success' in request.session:
        context['message'] = request.session.pop('pipeline_success')
    if 'pipeline_error' in request.session:
        context['error'] = request.session.pop('pipeline_error')

    if not SERVING_PATH.is_file():
        context['data_warning'] = 'Brak pliku serving/weather_pse_merged.csv. Uruchom potok danych.'
    else:
        try:
            context.update(build_dashboard(pd.read_csv(SERVING_PATH, low_memory=False)))
        except Exception:
            logger.exception('Błąd odczytu lub obliczeń dashboardu')
            context['data_warning'] = 'Nie udało się odczytać danych CSV. Szczegóły znajdują się w terminalu Django.'
    return render(request, 'index.html', context)