#!/usr/bin/env node
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const API_URL = 'https://open.er-api.com/v6/latest/USD';

// Monedas a trackear (además de USD, que es la base). Agregar/quitar códigos ISO 4217 acá.
const TRACKED_CURRENCIES = [
  'BOB', // Bolivia
  'ARS', // Argentina
  'BRL', // Brasil
  'CLP', // Chile
  'COP', // Colombia
  'PEN', // Perú
  'UYU', // Uruguay
  'MXN', // México
  'EUR', // Euro
];

async function fetchRates() {
  const res = await fetch(API_URL);
  if (!res.ok) {
    throw new Error(`Error al consultar ${API_URL}: HTTP ${res.status}`);
  }

  const data = await res.json();
  if (data.result !== 'success') {
    throw new Error(`Respuesta inesperada de la API: ${JSON.stringify(data)}`);
  }

  const rates = {};
  for (const code of TRACKED_CURRENCIES) {
    if (data.rates[code] === undefined) {
      console.warn(`Advertencia: no se encontró la moneda ${code} en la respuesta de la API`);
      continue;
    }
    rates[code] = data.rates[code];
  }

  return {
    updated_at: new Date().toISOString(),
    base: 'USD',
    source: API_URL,
    rates,
  };
}

async function main() {
  const snapshot = await fetchRates();

  const dataDir = path.join(process.cwd(), 'data');
  const historyDir = path.join(dataDir, 'history');
  await mkdir(historyDir, { recursive: true });

  const json = JSON.stringify(snapshot, null, 2) + '\n';

  await writeFile(path.join(dataDir, 'latest.json'), json);

  const today = snapshot.updated_at.slice(0, 10); // YYYY-MM-DD
  await writeFile(path.join(historyDir, `${today}.json`), json);

  console.log(`Tipos de cambio guardados (${today}):`);
  console.log(snapshot.rates);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
