import yfinance as yf
import pandas as pd
import numpy as np
import time

TASA_LIBRE_RIESGO = 0.045  # Fed Funds ~4.5%, ajustar según contexto macro


def estructurar_ticker(ticker: str, mercado: str = "USA") -> str:
    ticker = ticker.strip().upper()
    if mercado.upper() == "CHILE":
        return ticker if ticker.endswith(".SN") else f"{ticker}.SN"
    return ticker


def parsear_tickers(tickers: list[dict]) -> list[str]:
    """
    Acepta lista de dicts: [{"ticker": "SCHD", "mercado": "USA"}, ...]
    Devuelve lista de tickers formateados.
    """
    return [estructurar_ticker(t["ticker"], t.get("mercado", "USA")) for t in tickers]


def obtener_tipo_cambio_usdclp(periodo: str) -> pd.Series | None:
    try:
        datos = yf.download("CLPUSD=X", period=periodo, interval="1d",
                            auto_adjust=True, progress=False)
        # yfinance devuelve MultiIndex (Ticker, PriceType) incluso para un solo ticker
        tc = datos["CLPUSD=X"]["Close"] if "CLPUSD=X" in datos.columns.get_level_values(0) \
            else datos["Close"].squeeze()
        tc.name = "USDCLP"
        return tc
    except Exception:
        return None


def _extraer_serie(datos_raw: pd.DataFrame, ticker: str) -> pd.Series:
    """
    Extrae serie de precios de cierre ajustado.
    yfinance con group_by='ticker' siempre devuelve MultiIndex (Ticker, PriceType)
    independientemente del número de tickers.
    """
    level_0 = datos_raw.columns.get_level_values(0).unique().tolist()
    if ticker not in level_0:
        raise KeyError(f"{ticker} no encontrado en los datos descargados")
    return datos_raw[ticker]["Close"].dropna()


def obtener_metricas(tickers: list[dict], periodo: str = "1y") -> list[dict]:
    """
    Calcula métricas fundamentales y estadísticas para una lista de tickers.
    Normaliza activos chilenos a USD para comparabilidad.
    """
    lista_final = parsear_tickers(tickers)
    tickers_chile = [
        estructurar_ticker(t["ticker"], "CHILE")
        for t in tickers if t.get("mercado", "USA").upper() == "CHILE"
    ]

    if not lista_final:
        return []

    datos_raw = yf.download(
        lista_final, period=periodo, interval="1d",
        auto_adjust=True, group_by="ticker", progress=False
    )

    tc_usdclp = obtener_tipo_cambio_usdclp(periodo) if tickers_chile else None
    metricas_activos = []

    for ticker in lista_final:
        try:
            serie_precios = _extraer_serie(datos_raw, ticker)

            if ticker in tickers_chile and tc_usdclp is not None:
                tc_alineado = tc_usdclp.reindex(serie_precios.index, method="ffill")
                serie_precios = serie_precios * tc_alineado

            time.sleep(0.2)
            try:
                info = yf.Ticker(ticker).info
            except Exception:
                info = {}

            retornos_log = np.log(serie_precios / serie_precios.shift(1)).dropna()
            retorno_anualizado = float(retornos_log.mean() * 252)
            volatilidad_anualizada = float(retornos_log.std() * np.sqrt(252))
            sharpe = (
                (retorno_anualizado - TASA_LIBRE_RIESGO) / volatilidad_anualizada
                if volatilidad_anualizada > 0 else None
            )

            metricas_activos.append({
                "ticker": ticker,
                "nombre": info.get("longName"),
                "moneda": info.get("currency"),
                "precio_actual": info.get("currentPrice", info.get("previousClose")),
                "dividend_yield_pct": round((info.get("dividendYield", 0) or 0), 2),
                "trailing_per": info.get("trailingPE"),
                "retorno_anualizado_pct": round(retorno_anualizado * 100, 2),
                "volatilidad_anualizada_pct": round(volatilidad_anualizada * 100, 2),
                "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
            })

        except Exception as e:
            print(f"[ERROR] {ticker}: {type(e).__name__}: {e}")
            continue

    return metricas_activos


def obtener_historia(ticker: str, mercado: str = "USA", periodo: str = "1mo") -> list[dict]:
    """
    Devuelve la serie OHLCV diaria para un ticker.
    Fechas como string ISO para serialización JSON directa.
    """
    ticker_fmt = estructurar_ticker(ticker, mercado)
    try:
        df = yf.Ticker(ticker_fmt).history(period=periodo, auto_adjust=True)
        if df.empty:
            return []
        df.index = df.index.strftime("%Y-%m-%d")
        return [
            {
                "fecha": fecha,
                "open":   round(float(row["Open"]), 4),
                "high":   round(float(row["High"]), 4),
                "low":    round(float(row["Low"]), 4),
                "close":  round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            }
            for fecha, row in df.iterrows()
        ]
    except Exception as e:
        print(f"[ERROR] historia {ticker_fmt}: {type(e).__name__}: {e}")
        return []


def obtener_correlacion(tickers: list[dict], periodo: str = "1y") -> dict:
    """
    Calcula matriz de correlación de retornos logarítmicos normalizados a USD.
    """
    lista_final = parsear_tickers(tickers)
    tickers_chile = [
        estructurar_ticker(t["ticker"], "CHILE")
        for t in tickers if t.get("mercado", "USA").upper() == "CHILE"
    ]

    datos_raw = yf.download(
        lista_final, period=periodo, interval="1d",
        auto_adjust=True, group_by="ticker", progress=False
    )

    tc_usdclp = obtener_tipo_cambio_usdclp(periodo) if tickers_chile else None
    tabla_precios = pd.DataFrame()

    for ticker in lista_final:
        try:
            serie = _extraer_serie(datos_raw, ticker)

            if ticker in tickers_chile and tc_usdclp is not None:
                tc_alineado = tc_usdclp.reindex(serie.index, method="ffill")
                serie = serie * tc_alineado

            tabla_precios[ticker] = serie
        except Exception:
            continue

    retornos = np.log(tabla_precios / tabla_precios.shift(1)).dropna()
    return retornos.corr().round(2).to_dict()
