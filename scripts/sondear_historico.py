"""Sondeo temporal: busca una fuente de tipo de cambio oficial del BCB por fecha.

La idea es descubrir si existe algún endpoint que devuelva cotizaciones de días
pasados, para poder rellenar el histórico de golpe en vez de esperar a que el
cron acumule un snapshot por día.

Se ejecuta desde GitHub Actions (el sandbox de desarrollo no tiene salida a
internet). No forma parte del cron diario.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, timedelta

TIMEOUT = 25
UA = {"User-Agent": "Mozilla/5.0 (compatible; klotin-probe/1.0)"}

# Un día hábil reciente pero anterior a lo que ya tenemos guardado.
FECHA = date(2026, 7, 20)


def probe(url: str, nota: str = "") -> None:
    etiqueta = f"{url}" + (f"   [{nota}]" if nota else "")
    print(f"\n{'=' * 100}\nGET {etiqueta}")
    request = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status = response.status
            ctype = response.headers.get("Content-Type", "?")
            raw = response.read()
    except urllib.error.HTTPError as exc:
        print(f"  -> HTTP {exc.code} {exc.reason}")
        cuerpo = exc.read()[:300].decode("utf-8", errors="replace")
        if cuerpo.strip():
            print(f"  cuerpo: {cuerpo}")
        return
    except Exception as exc:  # noqa: BLE001 - queremos ver cualquier fallo
        print(f"  -> ERROR {type(exc).__name__}: {exc}")
        return

    texto = raw.decode("utf-8", errors="replace")
    print(f"  -> HTTP {status} | {ctype} | {len(raw)} bytes")

    if "json" in ctype.lower():
        try:
            data = json.loads(texto)
            print("  JSON:")
            print("  " + json.dumps(data, ensure_ascii=False, indent=2)[:2500].replace("\n", "\n  "))
            return
        except json.JSONDecodeError:
            pass
    print("  primeros 900 chars:")
    print("  " + texto[:900].replace("\n", "\n  "))


def main() -> None:
    f_iso = FECHA.isoformat()          # 2026-07-20
    f_bo = FECHA.strftime("%d/%m/%Y")  # 20/07/2026
    f_compacta = FECHA.strftime("%Y%m%d")

    print(f"Buscando cotización oficial del BCB para {f_iso}")

    # --- 1. API de CUCU: descubrir qué expone -------------------------------
    probe("https://apibcb.cucu.bo/api/v1/tc/oficial", "el que ya usa el cron: ver forma completa")
    probe("https://apibcb.cucu.bo/", "raíz, por si lista rutas")
    probe("https://apibcb.cucu.bo/api/v1", "índice de la v1")
    probe("https://apibcb.cucu.bo/api/v1/tc", "índice de tipo de cambio")
    probe("https://apibcb.cucu.bo/api/v1/tc/historico")
    probe("https://apibcb.cucu.bo/api/v1/tc/oficial/historico")
    probe(f"https://apibcb.cucu.bo/api/v1/tc/oficial?fecha={f_iso}")
    probe(f"https://apibcb.cucu.bo/api/v1/tc/oficial/{f_iso}")
    probe(f"https://apibcb.cucu.bo/api/v1/tc/oficial?date={f_iso}")

    # --- 2. Páginas del propio BCB ------------------------------------------
    probe(
        "https://www.bcb.gob.bo/tco_reporte_ultima_cotizacion.php",
        "la que ya scrapeamos para bancos: ver si acepta fecha",
    )
    probe(f"https://www.bcb.gob.bo/tco_reporte_ultima_cotizacion.php?fecha={f_bo}")
    probe(f"https://www.bcb.gob.bo/tco_reporte_cotizacion.php?fecha={f_bo}")
    probe("https://www.bcb.gob.bo/librerias/indicadores/tipocambio/tipocambio.php")
    probe(f"https://www.bcb.gob.bo/librerias/indicadores/tipocambio/tipocambio.php?fecha={f_bo}")
    probe(f"https://www.bcb.gob.bo/librerias/indicadores/tipocambio/tipocambio.php?fechaind={f_compacta}")

    # --- 3. APIs genéricas con histórico gratuito ---------------------------
    probe(f"https://api.frankfurter.app/{f_iso}?from=USD&to=BOB", "Frankfurter (BCE, quizá no tenga BOB)")
    probe(f"https://{f_iso}.currency-api.pages.dev/v1/currencies/usd.json", "currency-api (fawazahmed0)")
    probe(
        f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{f_iso}/v1/currencies/usd.json",
        "currency-api vía jsDelivr",
    )

    # --- 4. Rango de fechas del currency-api, si respondió -------------------
    print(f"\n{'=' * 100}\nPrueba de varios días seguidos en currency-api")
    for delta in range(0, 5):
        dia = (FECHA + timedelta(days=delta)).isoformat()
        url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{dia}/v1/currencies/usd.json"
        request = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
            print(f"  {dia}: BOB = {data.get('usd', {}).get('bob')}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {dia}: fallo -> {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
