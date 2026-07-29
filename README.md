# cron-tipos-cambio

Cron diario (GitHub Actions) que obtiene tipos de cambio contra el dólar (USD) y los guarda como JSON en este mismo repo. Pensado inicialmente para el boliviano (BOB), con otras monedas de la región incluidas.

## Cómo funciona

1. El workflow [`.github/workflows/daily-rates.yml`](.github/workflows/daily-rates.yml) corre todos los días a las 12:00 UTC (~08:00 hora Bolivia), y también se puede disparar manualmente desde la pestaña *Actions* (`workflow_dispatch`).
2. Ejecuta [`scripts/obtener_tipos_cambio.py`](scripts/obtener_tipos_cambio.py), que consulta una API pública gratuita ([open.er-api.com](https://www.exchangerate-api.com/docs/free), sin API key) con USD como moneda base.
3. Guarda el resultado en:
   - `data/latest.json`: el último valor obtenido (se sobreescribe cada corrida).
   - `data/history/YYYY-MM-DD.json`: un snapshot por día, para tener histórico.
   - `data/history.json`: array con los últimos 90 snapshots diarios, para que un front pueda graficar la tendencia sin pedir archivo por archivo.
4. Si hubo cambios, el workflow commitea y pushea automáticamente al repo.

## Formato del JSON

```json
{
  "updated_at": "2026-07-28T12:00:03.123Z",
  "base": "USD",
  "source": "https://open.er-api.com/v6/latest/USD",
  "rates": {
    "BOB": 6.96,
    "ARS": 1234.5,
    "BRL": 5.4,
    "CLP": 950.1,
    "COP": 4100.2,
    "PEN": 3.75,
    "UYU": 40.1,
    "MXN": 18.2,
    "EUR": 0.92
  },
  "bob_fuente": "Banco Central de Bolivia (bcb.gob.bo)",
  "bob_paralelo": {
    "source": "Binance P2P (USDT/BOB)",
    "compra": 11.91,
    "compra_muestras": 10,
    "venta": 11.94,
    "venta_muestras": 10,
    "value": 11.92
  },
  "bob_brecha_pct": 1.03,
  "bob_oficial_var_pct": 0.15,
  "bob_paralelo_var_pct": -0.42
}
```

`rates` son unidades de esa moneda por 1 USD. Para el resto de las monedas es el tipo de cambio oficial de [open.er-api.com](https://www.exchangerate-api.com/docs/free); para `BOB` específicamente, se obtiene directo del **Banco Central de Bolivia** (vía la [API pública de CUCU](https://docs.cucu.bo/bcb-api), que republica en JSON las cifras oficiales del BCB) — `bob_fuente` indica de dónde salió ese valor en cada corrida, incluyendo si hubo que usar el respaldo (`open.er-api.com`) porque el BCB no estaba disponible.

`bob_paralelo` es el dólar paralelo boliviano, estimado con anuncios de USDT/BOB en Binance P2P: `compra` es el precio promedio para comprar dólares paralelos (gente vendiendo USDT), `venta` el precio promedio para vender (gente comprando USDT), y `value` el promedio de ambos. Si Binance falla, el campo completo no aparece en esa corrida (el resto de los datos se guarda igual).

`bob_brecha_pct` es la diferencia porcentual entre el paralelo (`bob_paralelo.value`) y el oficial (`rates.BOB`). Solo aparece si se pudo calcular el paralelo.

`bob_oficial_var_pct` y `bob_paralelo_var_pct` son la variación porcentual respecto al snapshot anterior guardado en `data/history/`. Solo aparecen si existe un snapshot previo (y, en el caso del paralelo, si ambos días tienen ese dato).

## Monedas incluidas

Boliviano (BOB), peso argentino (ARS), real (BRL), peso chileno (CLP), peso colombiano (COP), sol peruano (PEN), peso uruguayo (UYU), peso mexicano (MXN) y euro (EUR). Para agregar o quitar monedas, editar la lista `TRACKED_CURRENCIES` en `scripts/obtener_tipos_cambio.py` (usar códigos ISO 4217).

## Sobre el tipo de cambio boliviano

Este cron usa el **tipo de cambio oficial** publicado por la API (equivalente al fijado por el Banco Central de Bolivia). El **dólar paralelo/informal** no está incluido porque no hay una API pública confiable y gratuita para obtenerlo automáticamente; si tenés una fuente específica en mente, se puede sumar como un scraper aparte.

## Correr localmente

```bash
python3 scripts/obtener_tipos_cambio.py
```

Requiere Python >= 3.10 (usa `urllib` de la librería estándar, sin dependencias externas).
