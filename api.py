import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
import os

from core import obtener_metricas, obtener_correlacion

# --- Auth ---
API_KEY = os.environ.get("API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verificar_api_key(key: str = Security(api_key_header)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY no configurada en el servidor")
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="API Key inválida")
    return key

# --- Caché en memoria ---
_cache: dict[str, dict] = {}
CACHE_TTL_SEGUNDOS = 900  # 15 minutos

def cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL_SEGUNDOS:
        return entry["data"]
    return None

def cache_set(key: str, data: Any):
    _cache[key] = {"ts": time.time(), "data": data}

# --- Modelos ---
class TickerItem(BaseModel):
    ticker: str
    mercado: str = "USA"  # "USA" o "CHILE"

class ConsultaRequest(BaseModel):
    tickers: list[TickerItem] = Field(..., max_length=20)
    periodo: str = "1y"  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y

# --- App ---
app = FastAPI(
    title="yfinance API",
    description="API REST para consulta de métricas financieras de tickers USA y Chile",
    version="1.0.0",
)

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.post("/metricas", dependencies=[Depends(verificar_api_key)])
def metricas(body: ConsultaRequest):
    """
    Devuelve métricas fundamentales y estadísticas para hasta 20 tickers.
    Resultado cacheado 15 minutos.
    """
    tickers_dict = [t.model_dump() for t in body.tickers]
    cache_key = f"metricas:{sorted(str(tickers_dict))}:{body.periodo}"

    cached = cache_get(cache_key)
    if cached:
        return {"source": "cache", "data": cached}

    resultado = obtener_metricas(tickers_dict, body.periodo)
    cache_set(cache_key, resultado)
    return {"source": "live", "data": resultado}

@app.post("/correlacion", dependencies=[Depends(verificar_api_key)])
def correlacion(body: ConsultaRequest):
    """
    Devuelve matriz de correlación de retornos logarítmicos normalizados a USD.
    Resultado cacheado 15 minutos.
    """
    tickers_dict = [t.model_dump() for t in body.tickers]
    cache_key = f"correlacion:{sorted(str(tickers_dict))}:{body.periodo}"

    cached = cache_get(cache_key)
    if cached:
        return {"source": "cache", "data": cached}

    resultado = obtener_correlacion(tickers_dict, body.periodo)
    cache_set(cache_key, resultado)
    return {"source": "cache", "data": resultado}
