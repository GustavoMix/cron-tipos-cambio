# cron-tipos-cambio

Cron diario (GitHub Actions) que obtiene tipos de cambio contra el dólar (USD) y los guarda como JSON en este mismo repo. Pensado inicialmente para el boliviano (BOB), con otras monedas de la región incluidas.

## Cómo funciona

1. El workflow [`.github/workflows/daily-rates.yml`](.github/workflows/daily-rates.yml) corre todos los días a las 12:00 UTC (~08:00 hora Bolivia), y también se puede disparar manualmente desde la pestaña *Actions* (`workflow_dispatch`).
2. Ejecuta [`scripts/fetch-rates.mjs`](scripts/fetch-rates.mjs), que consulta una API pública gratuita ([open.er-api.com](https://www.exchangerate-api.com/docs/free), sin API key) con USD como moneda base.
3. Guarda el resultado en:
   - `data/latest.json`: el último valor obtenido (se sobreescribe cada corrida).
   - `data/history/YYYY-MM-DD.json`: un snapshot por día, para tener histórico.
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
  }
}
```

`rates` son unidades de esa moneda por 1 USD.

## Monedas incluidas

Boliviano (BOB), peso argentino (ARS), real (BRL), peso chileno (CLP), peso colombiano (COP), sol peruano (PEN), peso uruguayo (UYU), peso mexicano (MXN) y euro (EUR). Para agregar o quitar monedas, editar el array `TRACKED_CURRENCIES` en `scripts/fetch-rates.mjs` (usar códigos ISO 4217).

## Sobre el tipo de cambio boliviano

Este cron usa el **tipo de cambio oficial** publicado por la API (equivalente al fijado por el Banco Central de Bolivia). El **dólar paralelo/informal** no está incluido porque no hay una API pública confiable y gratuita para obtenerlo automáticamente; si tenés una fuente específica en mente, se puede sumar como un scraper aparte.

## Correr localmente

```bash
npm run fetch
```

Requiere Node.js >= 20 (usa `fetch` nativo, sin dependencias externas).
