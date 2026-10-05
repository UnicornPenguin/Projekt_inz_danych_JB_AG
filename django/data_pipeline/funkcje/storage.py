import json

from datetime import datetime, timezone

from django.conf import settings

DATA_DIR = settings.BASE_DIR / "data"

def save_raw(data):

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S_%f")

    folder = DATA_DIR / "raw"
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{run_id}.json"

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "downloaded_at": now.isoformat(),
                "data": data,
            },
            file,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

    print(f"Zapisano raw: {path}", flush=True)

    return run_id