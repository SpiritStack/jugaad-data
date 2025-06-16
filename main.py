from fastapi import FastAPI, Query
from typing import Optional
from jugaad_data.nse import stock_df, index_df, get_stock_symbols, get_index_symbols, get_expiry_dates, option_chain
from datetime import date
import pandas as pd

app = FastAPI(title="Jugaad NSE Data API", version="1.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Jugaad NSE Data API"}

@app.get("/symbols/stocks")
def get_stocks():
    return get_stock_symbols()

@app.get("/symbols/indexes")
def get_indexes():
    return get_index_symbols()

@app.get("/stock-data")
def get_stock_data(symbol: str, start: date, end: date):
    df = stock_df(symbol=symbol, from_date=start, to_date=end, series="EQ")
    return df.to_dict(orient="records")

@app.get("/index-data")
def get_index_data(symbol: str, start: date, end: date):
    df = index_df(symbol=symbol, from_date=start, to_date=end)
    return df.to_dict(orient="records")

@app.get("/fo/expiry-dates")
def fo_expiry_dates():
    return get_expiry_dates()

@app.get("/fo/option-chain")
def option_chain_data(symbol: str, expiry: Optional[str] = None):
    df = option_chain(symbol, expiry=expiry)
    return df.to_dict(orient="records")
