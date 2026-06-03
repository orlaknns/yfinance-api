# yFinance API — Documentación Técnica

**URL Base:** `https://yfinance-api-prod.up.railway.app`  
**Versión:** 1.0.0  
**Fuente de datos:** Yahoo Finance vía librería `yfinance >= 0.2.x`

---

## Autenticación

Todos los endpoints excepto `/health` requieren el header:

```
X-API-Key: <tu_api_key>
```

| Código | Descripción |
|--------|-------------|
| `403` | API Key inválida o ausente |
| `500` | API Key no configurada en el servidor |

---

## Endpoints

### `GET /health`

Verifica que el servicio está online. No requiere autenticación.

**Respuesta:**
```json
{
  "status": "ok",
  "timestamp": "2026-06-03T20:13:02.999371"
}
```

---

### `POST /metricas`

Devuelve métricas fundamentales y estadísticas para hasta **20 tickers**. Los activos chilenos se convierten automáticamente a USD para comparabilidad. Resultado cacheado 15 minutos.

**Request body:**
```json
{
  "tickers": [
    { "ticker": "SCHD", "mercado": "USA" },
    { "ticker": "COPEC", "mercado": "CHILE" }
  ],
  "periodo": "1y"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `tickers` | array | Sí | Lista de hasta 20 tickers |
| `tickers[].ticker` | string | Sí | Símbolo del activo (sin sufijo para Chile) |
| `tickers[].mercado` | string | No | `"USA"` (default) o `"CHILE"` |
| `periodo` | string | No | Período histórico. Default: `"1y"` |

**Períodos válidos:**

| Valor | Descripción |
|-------|-------------|
| `1d` | 1 día |
| `5d` | 5 días |
| `1mo` | 1 mes |
| `3mo` | 3 meses |
| `6mo` | 6 meses |
| `1y` | 1 año (default) |
| `2y` | 2 años |
| `5y` | 5 años |
| `10y` | 10 años |
| `ytd` | Año actual |
| `max` | Máximo histórico disponible |

**Respuesta:**
```json
{
  "source": "live",
  "tickers_procesados": 2,
  "data": [
    {
      "ticker": "SCHD",
      "nombre": "Schwab U.S. Dividend Equity ETF",
      "moneda": "USD",
      "precio_actual": 32.37,
      "dividend_yield_pct": 3.29,
      "trailing_per": 19.20,
      "retorno_anualizado_pct": 24.79,
      "volatilidad_anualizada_pct": 10.94,
      "sharpe_ratio": 1.86
    }
  ]
}
```

| Campo respuesta | Descripción | Fuente |
|----------------|-------------|--------|
| `source` | `"live"` o `"cache"` | Interno |
| `tickers_procesados` | Cantidad de tickers con datos válidos | Interno |
| `ticker` | Símbolo formateado (ej: `COPEC.SN`) | yfinance |
| `nombre` | Nombre completo del activo | `info.longName` |
| `moneda` | Moneda original del activo | `info.currency` |
| `precio_actual` | Precio de cierre más reciente | `info.currentPrice` |
| `dividend_yield_pct` | Dividend yield en % (ej: 3.29 = 3.29%) | `info.dividendYield` |
| `trailing_per` | Price/Earnings ratio trailing 12m | `info.trailingPE` |
| `retorno_anualizado_pct` | Retorno anualizado histórico en % | Calculado: `log_ret.mean() * 252` |
| `volatilidad_anualizada_pct` | Volatilidad anualizada en % | Calculado: `log_ret.std() * √252` |
| `sharpe_ratio` | Sharpe Ratio vs tasa libre 4.5% | Calculado: `(ret - rf) / vol` |

---

### `POST /correlacion`

Devuelve la matriz de correlación de retornos logarítmicos diarios entre todos los tickers del request, normalizados a USD. Resultado cacheado 15 minutos.

**Request body:** mismo formato que `/metricas`.

**Respuesta:**
```json
{
  "source": "live",
  "data": {
    "SCHD": { "SCHD": 1.0, "DGRO": 0.91, "COPEC.SN": 0.12 },
    "DGRO": { "SCHD": 0.91, "DGRO": 1.0, "COPEC.SN": 0.10 },
    "COPEC.SN": { "SCHD": 0.12, "DGRO": 0.10, "COPEC.SN": 1.0 }
  }
}
```

**Interpretación:**

| Rango | Significado para la cartera |
|-------|----------------------------|
| `0.9 – 1.0` | Activos prácticamente idénticos, sin diversificación |
| `0.5 – 0.9` | Correlación moderada, diversificación parcial |
| `0.0 – 0.5` | Baja correlación, buena diversificación |
| `< 0.0` | Correlación negativa, diversificación óptima |

---

## Toda la información disponible desde yfinance

La API actualmente expone un subconjunto. A continuación el inventario completo de lo que `yf.Ticker(ticker).info` provee y que puede incorporarse en versiones futuras:

### Precio y volumen
| Campo yfinance | Descripción |
|---------------|-------------|
| `currentPrice` | Precio actual |
| `previousClose` | Cierre anterior |
| `open` | Apertura del día |
| `dayHigh` / `dayLow` | Máximo/mínimo del día |
| `fiftyTwoWeekHigh` / `fiftyTwoWeekLow` | Rango 52 semanas |
| `fiftyDayAverage` / `twoHundredDayAverage` | Medias móviles 50/200 días |
| `volume` / `averageVolume` | Volumen actual y promedio |
| `marketCap` | Capitalización de mercado |

### Dividendos
| Campo yfinance | Descripción |
|---------------|-------------|
| `dividendYield` | Yield actual (ya en %, ej: 3.29) |
| `dividendRate` | Dividendo anual por acción en moneda local |
| `exDividendDate` | Fecha ex-dividendo (unix timestamp) |
| `lastDividendValue` | Último dividendo pagado |
| `lastDividendDate` | Fecha del último dividendo |
| `payoutRatio` | % de earnings distribuido como dividendo |
| `fiveYearAvgDividendYield` | Yield promedio 5 años |

### Valoración
| Campo yfinance | Descripción |
|---------------|-------------|
| `trailingPE` | PER trailing 12 meses |
| `forwardPE` | PER forward (estimado próximos 12m) |
| `priceToBook` | Precio / Valor en libros |
| `priceToSalesTrailing12Months` | Precio / Ventas 12m |
| `enterpriseValue` | Valor empresa (EV) |
| `enterpriseToRevenue` | EV / Ingresos |
| `enterpriseToEbitda` | EV / EBITDA |
| `pegRatio` | PEG Ratio (PER / crecimiento earnings) |

### Rentabilidad y márgenes
| Campo yfinance | Descripción |
|---------------|-------------|
| `profitMargins` | Margen neto |
| `grossMargins` | Margen bruto |
| `operatingMargins` | Margen operacional |
| `ebitdaMargins` | Margen EBITDA |
| `returnOnAssets` | ROA |
| `returnOnEquity` | ROE |

### Crecimiento
| Campo yfinance | Descripción |
|---------------|-------------|
| `earningsGrowth` | Crecimiento YoY de earnings |
| `revenueGrowth` | Crecimiento YoY de ingresos |
| `earningsQuarterlyGrowth` | Crecimiento trimestral de earnings |

### Balance y deuda
| Campo yfinance | Descripción |
|---------------|-------------|
| `totalCash` | Caja total |
| `totalDebt` | Deuda total |
| `debtToEquity` | Ratio deuda/patrimonio |
| `currentRatio` | Ratio corriente (liquidez) |
| `quickRatio` | Prueba ácida |
| `freeCashflow` | Free cash flow |

### Analistas y recomendaciones
| Campo yfinance | Descripción |
|---------------|-------------|
| `targetHighPrice` / `targetLowPrice` | Precio objetivo alto/bajo de analistas |
| `targetMeanPrice` | Precio objetivo promedio |
| `recommendationMean` | Score consenso (1=Compra fuerte, 5=Venta fuerte) |
| `recommendationKey` | `"buy"`, `"hold"`, `"sell"`, etc. |
| `numberOfAnalystOpinions` | Número de analistas cubriendo el activo |

### Datos adicionales via otros métodos yfinance
| Método | Descripción |
|--------|-------------|
| `yf.Ticker.history()` | Serie histórica OHLCV completa |
| `yf.Ticker.dividends` | Historial completo de dividendos |
| `yf.Ticker.splits` | Historial de splits |
| `yf.Ticker.financials` | Estado de resultados anual |
| `yf.Ticker.quarterly_financials` | Estado de resultados trimestral |
| `yf.Ticker.balance_sheet` | Balance general anual |
| `yf.Ticker.cashflow` | Flujo de caja anual |
| `yf.Ticker.institutional_holders` | Tenedores institucionales |
| `yf.Ticker.major_holders` | Accionistas mayoritarios |
| `yf.Ticker.options` | Cadena de opciones disponibles |

---

## Restricciones y limitaciones

### Yahoo Finance (fuente de datos)
| Restricción | Detalle |
|-------------|---------|
| **Rate limiting** | No documentado oficialmente. Exceder ~2.000 requests/hora por IP puede resultar en bloqueo temporal (HTTP 429 o 401) |
| **Sin API key oficial** | yfinance hace scraping de Yahoo Finance. No hay SLA ni garantía de disponibilidad |
| **Datos con retraso** | Precios en tiempo real solo para mercados USA durante horario de mercado. Chile (S&P CLX) puede tener retraso de 15-20 min |
| **Tickers deslistados** | `.info` puede devolver `{}` o lanzar excepción para activos suspendidos o delisted |
| **Cobertura IPSA** | No todos los activos del IPSA tienen datos completos. Activos con baja liquidez pueden tener gaps en la serie histórica |
| **Campos nulos** | Campos como `trailingPE`, `forwardPE` pueden ser `null` para ETFs, fondos o activos sin earnings |
| **Cambios de API** | yfinance ha cambiado su estructura de datos en versiones menores sin aviso (ej: MultiIndex orientation). Versión fijada en `requirements.txt` |

### Esta API
| Restricción | Detalle |
|-------------|---------|
| **Máximo 20 tickers por request** | Límite de diseño para evitar timeouts (cada ticker agrega ~0.2s de espera) |
| **Caché de 15 minutos** | Dos requests idénticos dentro de 15 min devuelven el mismo dato. `source: "cache"` indica esto |
| **Caché volátil** | La caché vive en memoria del proceso. Un reinicio del servidor (deploy, crash) la borra |
| **Sin datos intraday** | El pipeline usa `interval="1d"`. No apto para estrategias intraday |
| **Tasa libre de riesgo fija** | Sharpe calculado con rf=4.5% hardcodeada. No se actualiza automáticamente |
| **Latencia variable** | Un request de 20 tickers puede tardar 15-25 segundos en frío (sin caché) |

---

## Suite de pruebas

### 1. Health check
```bash
curl -s https://yfinance-api-prod.up.railway.app/health
```
**Resultado esperado:** `{"status":"ok","timestamp":"..."}`

---

### 2. Autenticación — key válida
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{"tickers": [{"ticker": "AAPL"}], "periodo": "1mo"}'
```
**Resultado esperado:** `{"source":"live","data":[{...}]}`

---

### 3. Autenticación — key inválida
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: clave-incorrecta" \
  -d '{"tickers": [{"ticker": "AAPL"}]}'
```
**Resultado esperado:** `{"detail":"API Key inválida"}` HTTP 403

---

### 4. Un ticker USA
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{"tickers": [{"ticker": "SCHD", "mercado": "USA"}], "periodo": "1y"}' \
  | python3 -m json.tool
```
**Resultado esperado:** SCHD con `sharpe_ratio` > 0, `dividend_yield_pct` ~3.3%

---

### 5. Cartera mixta USA + Chile
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{
    "tickers": [
      {"ticker": "SCHD", "mercado": "USA"},
      {"ticker": "DGRO", "mercado": "USA"},
      {"ticker": "JEPQ", "mercado": "USA"},
      {"ticker": "COPEC", "mercado": "CHILE"},
      {"ticker": "CENCOSUD", "mercado": "CHILE"}
    ],
    "periodo": "1y"
  }' | python3 -m json.tool
```
**Resultado esperado:** 5 tickers procesados, `tickers_procesados: 5`

---

### 6. Correlación de cartera
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/correlacion \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{
    "tickers": [
      {"ticker": "SCHD", "mercado": "USA"},
      {"ticker": "DGRO", "mercado": "USA"},
      {"ticker": "COPEC", "mercado": "CHILE"}
    ],
    "periodo": "1y"
  }' | python3 -m json.tool
```
**Resultado esperado:** matriz 3x3 con diagonal = 1.0

---

### 7. Validación — exceder límite de 20 tickers
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{
    "tickers": [
      {"ticker":"AAPL"},{"ticker":"MSFT"},{"ticker":"GOOG"},{"ticker":"AMZN"},
      {"ticker":"META"},{"ticker":"NVDA"},{"ticker":"TSLA"},{"ticker":"BRK-B"},
      {"ticker":"JPM"},{"ticker":"V"},{"ticker":"UNH"},{"ticker":"XOM"},
      {"ticker":"JNJ"},{"ticker":"WMT"},{"ticker":"PG"},{"ticker":"MA"},
      {"ticker":"HD"},{"ticker":"CVX"},{"ticker":"MRK"},{"ticker":"ABBV"},
      {"ticker":"EXTRA"}
    ]
  }'
```
**Resultado esperado:** HTTP 422 Unprocessable Entity

---

### 8. Verificar caché
```bash
# Primer request (live)
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{"tickers": [{"ticker": "AAPL"}], "periodo": "1y"}' | python3 -m json.tool

# Segundo request inmediato (debe responder desde caché)
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{"tickers": [{"ticker": "AAPL"}], "periodo": "1y"}' | python3 -m json.tool
```
**Resultado esperado:** primer request `"source":"live"`, segundo `"source":"cache"`

---

### 9. Ticker inválido o inexistente
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{"tickers": [{"ticker": "TICKERINEXISTENTE123"}], "periodo": "1y"}' \
  | python3 -m json.tool
```
**Resultado esperado:** `{"source":"live","data":[],"tickers_procesados":0}`

---

### 10. Período máximo histórico
```bash
curl -s -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: bbP28WBCw6NGZ-FDFNI88nr8kQpAwZPRA9YiQsDN8Zk" \
  -d '{"tickers": [{"ticker": "SCHD"}], "periodo": "max"}' \
  | python3 -m json.tool
```
**Resultado esperado:** métricas calculadas sobre el histórico completo disponible (SCHD desde 2011)

---

## Notas de integración para sistema de alertas

- El campo `source` permite saber si el dato viene de cache o es fresco. Para alertas críticas puedes ignorar respuestas `"cache"` y reintentar después del TTL
- Para polling frecuente (< 15 min), el segundo request siempre será `cache` — no consume quota de Yahoo Finance
- Si un ticker falla (red, delisted), simplemente no aparece en `data`. Verificar siempre `tickers_procesados` vs cantidad enviada
- El `sharpe_ratio` negativo (como COPEC.SN = -0.10) es una señal directa para tu motor de alertas
