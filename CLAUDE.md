# CLAUDE.md — yFinance API

## Descripción del proyecto

API REST construida con FastAPI que expone métricas financieras de tickers USA y Chile (IPSA) obtenidas vía `yfinance`. Diseñada para ser consumida por un sistema externo de alertas de inversiones con polling periódico.

## URLs y acceso

| Entorno | URL |
|---------|-----|
| Producción | `https://yfinance-api-prod.up.railway.app` |
| Docs interactivos | `https://yfinance-api-prod.up.railway.app/docs` |

**Autenticación:** header `X-API-Key` en cada request (excepto `/health`).
La API Key está configurada como variable de entorno `API_KEY` en Railway.

## Infraestructura

- **Hosting:** Railway — proyecto `yFinance-API`
- **Deploy:** automático en cada push a `main` (GitHub repo: `orlaknns/yfinance-api`)
- **Caché:** en memoria, TTL 15 minutos — se resetea al reiniciar el servicio
- **Sin base de datos ni Redis** — diseño intencional para mantener simplicidad operacional

## Estructura de archivos

```
core.py          # Lógica pura: descarga yfinance, cálculo de métricas y correlación
api.py           # FastAPI: endpoints, caché en memoria, autenticación por API Key
requirements.txt # Dependencias Python
railway.toml     # Configuración de build y start command para Railway
```

## Endpoints

### `GET /health`
Sin autenticación. Verifica que el servicio está online.
```json
{"status": "ok", "timestamp": "2026-06-03T20:13:02.999371"}
```

### `POST /metricas`
Devuelve métricas fundamentales y estadísticas para hasta 20 tickers.
```bash
curl -X POST https://yfinance-api-prod.up.railway.app/metricas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
    "tickers": [
      {"ticker": "SCHD", "mercado": "USA"},
      {"ticker": "COPEC", "mercado": "CHILE"}
    ],
    "periodo": "1y"
  }'
```

### `POST /correlacion`
Devuelve matriz de correlación de retornos logarítmicos normalizados a USD.
Mismo formato de request que `/metricas`.

## Convenciones críticas de `core.py`

### yfinance >= 0.2.x — MultiIndex
`yf.download()` con múltiples tickers devuelve MultiIndex `(PriceType, Ticker)`.
Con un solo ticker devuelve columnas simples. Se maneja vía `_extraer_serie()`:
```python
# MultiIndex (múltiples tickers)
datos_raw["Close"][ticker]
# Columnas simples (un solo ticker)
datos_raw["Close"]
```

### Retornos logarítmicos
Todos los cálculos usan retornos log, no `pct_change()`:
```python
retornos = np.log(precios / precios.shift(1)).dropna()
```

### Normalización FX
Activos chilenos (`.SN`) se convierten a USD via `CLPUSD=X` antes de calcular métricas. La correlación entre mercados es inválida sin esta normalización.

### Tasa libre de riesgo
```python
TASA_LIBRE_RIESGO = 0.045  # Fed Funds ~4.5%
```
Definida al tope de `core.py`. Actualizar según contexto macro.

## Periodos válidos para `periodo`

`1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y`

## Métricas devueltas por ticker

| Campo | Descripción |
|-------|-------------|
| `retorno_anualizado_pct` | `retornos_log.mean() * 252 * 100` |
| `volatilidad_anualizada_pct` | `retornos_log.std() * sqrt(252) * 100` |
| `sharpe_ratio` | `(retorno - tasa_libre) / volatilidad` |
| `dividend_yield_pct` | Vía `yf.Ticker.info["dividendYield"]` |
| `trailing_per` | Vía `yf.Ticker.info["trailingPE"]` |

## Deploy manual (si falla el auto-deploy)

```bash
cd yfinance-api
railway up --service yFinance-API
```
