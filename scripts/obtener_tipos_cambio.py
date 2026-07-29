#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://open.er-api.com/v6/latest/USD"
BCB_OFICIAL_URL = "https://apibcb.cucu.bo/api/v1/tc/oficial"
BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
HISTORIAL_DIAS = 90

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


def fetch_bcb_oficial() -> float | None:
    """Tipo de cambio oficial del boliviano, publicado por el Banco Central de Bolivia
    (vía la API pública de CUCU, que republica en JSON las cifras del BCB)."""
    try:
        with urllib.request.urlopen(BCB_OFICIAL_URL, timeout=30) as response:
            if response.status != 200:
                print(f"Advertencia: API del BCB respondió HTTP {response.status}")
                return None
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"Advertencia: no se pudo consultar la API del BCB: {exc}")
        return None

    value = data.get("tc_oficial", {}).get("compra")
    if value is None:
        print("Advertencia: la API del BCB no devolvió el valor esperado")
        return None

    return float(value)


def _fetch_binance_p2p_average(trade_type: str, rows: int = 10) -> tuple[float, int] | None:
    payload = json.dumps(
        {
            "asset": "USDT",
            "fiat": "BOB",
            "tradeType": trade_type,
            "page": 1,
            "rows": rows,
            "payTypes": [],
            "publisherType": None,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        BINANCE_P2P_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                print(f"Advertencia: Binance P2P respondió HTTP {response.status} ({trade_type})")
                return None
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"Advertencia: no se pudo consultar Binance P2P ({trade_type}): {exc}")
        return None

    ads = data.get("data") or []
    prices = [float(ad["adv"]["price"]) for ad in ads if ad.get("adv", {}).get("price")]
    if not prices:
        print(f"Advertencia: Binance P2P no devolvió anuncios para USDT/BOB ({trade_type})")
        return None

    return sum(prices) / len(prices), len(prices)


def fetch_bob_paralelo(rows: int = 10) -> dict | None:
    """Precio del dólar paralelo boliviano, estimado con anuncios de USDT/BOB en Binance P2P.

    Se consultan ambos lados del mercado (gente vendiendo USDT = precio de compra
    del dólar paralelo para el usuario; gente comprando USDT = precio de venta).
    """
    compra = _fetch_binance_p2p_average("SELL", rows)
    venta = _fetch_binance_p2p_average("BUY", rows)

    if compra is None and venta is None:
        return None

    result = {"source": "Binance P2P (USDT/BOB)"}
    if compra is not None:
        result["compra"] = round(compra[0], 4)
        result["compra_muestras"] = compra[1]
    if venta is not None:
        result["venta"] = round(venta[0], 4)
        result["venta_muestras"] = venta[1]

    if compra is not None and venta is not None:
        result["value"] = round((compra[0] + venta[0]) / 2, 4)
    else:
        result["value"] = result.get("compra") or result.get("venta")

    return result


def _pct_change(actual: float, anterior: float) -> float:
    return round((actual - anterior) / anterior * 100, 2)


def _cargar_snapshot_anterior(history_dir: Path, antes_de: str) -> dict | None:
    archivos = sorted(p for p in history_dir.glob("*.json") if p.stem < antes_de)
    if not archivos:
        return None
    return json.loads(archivos[-1].read_text(encoding="utf-8"))


def _reconstruir_historial(history_dir: Path, data_dir: Path) -> None:
    archivos = sorted(history_dir.glob("*.json"))[-HISTORIAL_DIAS:]
    historial = [json.loads(p.read_text(encoding="utf-8")) for p in archivos]
    texto = json.dumps(historial, indent=2, ensure_ascii=False) + "\n"
    (data_dir / "history.json").write_text(texto, encoding="utf-8")


def main() -> None:
    snapshot = fetch_rates()

    bcb_oficial = fetch_bcb_oficial()
    if bcb_oficial is not None:
        snapshot["rates"]["BOB"] = bcb_oficial
        snapshot["bob_fuente"] = "Banco Central de Bolivia (bcb.gob.bo)"
    else:
        snapshot["bob_fuente"] = f"{API_URL} (BCB no disponible, se usó respaldo)"

    bob_paralelo = fetch_bob_paralelo()
    if bob_paralelo is not None:
        snapshot["bob_paralelo"] = bob_paralelo
        oficial = snapshot["rates"]["BOB"]
        snapshot["bob_brecha_pct"] = _pct_change(bob_paralelo["value"], oficial)

    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    history_dir = data_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    today = snapshot["updated_at"][:10]  # YYYY-MM-DD

    anterior = _cargar_snapshot_anterior(history_dir, today)
    if anterior is not None:
        snapshot["bob_oficial_var_pct"] = _pct_change(
            snapshot["rates"]["BOB"], anterior["rates"]["BOB"]
        )
        if bob_paralelo is not None and anterior.get("bob_paralelo"):
            snapshot["bob_paralelo_var_pct"] = _pct_change(
                bob_paralelo["value"], anterior["bob_paralelo"]["value"]
            )

    text = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"

    (data_dir / "latest.json").write_text(text, encoding="utf-8")
    (history_dir / f"{today}.json").write_text(text, encoding="utf-8")

    _reconstruir_historial(history_dir, data_dir)

    print(f"Tipos de cambio guardados ({today}):")
    print(snapshot["rates"])
    if bob_paralelo is not None:
        print(f"Dólar paralelo BOB (Binance P2P): {bob_paralelo['value']} (brecha {snapshot['bob_brecha_pct']}%)")


if __name__ == "__main__":
    main()
