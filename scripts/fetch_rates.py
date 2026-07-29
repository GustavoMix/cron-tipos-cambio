#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://open.er-api.com/v6/latest/USD"

# Monedas a trackear (además de USD, que es la base). Agregar/quitar códigos ISO 4217 acá.
TRACKED_CURRENCIES = [
    "BOB",  # Bolivia
    "ARS",  # Argentina
    "BRL",  # Brasil
    "CLP",  # Chile
    "COP",  # Colombia
    "PEN",  # Perú
    "UYU",  # Uruguay
    "MXN",  # México
    "EUR",  # Euro
]


def fetch_rates() -> dict:
    try:
        with urllib.request.urlopen(API_URL, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"Error al consultar {API_URL}: HTTP {response.status}")
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Error al consultar {API_URL}: {exc}") from exc

    if data.get("result") != "success":
        raise RuntimeError(f"Respuesta inesperada de la API: {data}")

    rates = {}
    for code in TRACKED_CURRENCIES:
        value = data["rates"].get(code)
        if value is None:
            print(f"Advertencia: no se encontró la moneda {code} en la respuesta de la API")
            continue
        rates[code] = value

    now = datetime.now(timezone.utc)
    updated_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

    return {
        "updated_at": updated_at,
        "base": "USD",
        "source": API_URL,
        "rates": rates,
    }


def main() -> None:
    snapshot = fetch_rates()

    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    history_dir = data_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    text = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"

    (data_dir / "latest.json").write_text(text, encoding="utf-8")

    today = snapshot["updated_at"][:10]  # YYYY-MM-DD
    (history_dir / f"{today}.json").write_text(text, encoding="utf-8")

    print(f"Tipos de cambio guardados ({today}):")
    print(snapshot["rates"])


if __name__ == "__main__":
    main()
