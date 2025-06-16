from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
import pandas as pd
import os

from jugaad_data.nse import stock_df, index_df
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import json

from dotenv import load_dotenv
load_dotenv()


# --- FastAPI App ---

app = FastAPI(
    title="Jugaad Data NSE API",
    description="FastAPI wrapper for NSE stock/index data using jugaad-data.\n\n"
                "Features:\n"
                "- Fetch historical stock/index data\n"
                "- Filter for F&O stocks only\n"
                "- Uses MongoDB cache if available\n",
    version="1.1.0"
)

# --- Pydantic Models ---

class StockData(BaseModel):
    DATE: str
    SYMBOL: str
    OPEN: float
    HIGH: float
    LOW: float
    CLOSE: float
    VOLUME: int

class IndexData(BaseModel):
    DATE: str
    SYMBOL: str
    OPEN: float
    HIGH: float
    LOW: float
    CLOSE: float
    VOLUME: Optional[int] = None

# --- MongoDB Setup ---

mongo_client = None
stock_cache = None
try:
    mongo_url = os.environ.get("MONGO_URL")
    if mongo_url:
        mongo_client = MongoClient(mongo_url)
        mongo_client.admin.command('ping')  # Check connection
        db = mongo_client["jugaad_cache"]
        stock_cache = db["stock_data"]
except Exception as e:
    print("⚠️ MongoDB not available. Skipping DB caching.")

# --- Helper: F&O Symbols ---

def get_fno_symbols() -> List[str]:
    """
    Reads F&O symbols from CSV packaged with jugaad_data.
    """
    fno_csv = os.path.join(os.path.dirname(__import__('jugaad_data').__file__), "resources", "nse_fo_mkt_symbols.csv")
    df = pd.read_csv(fno_csv)
    return df["SYMBOL"].unique().tolist()

# --- API Routes ---

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "📈 Welcome to the Jugaad Data API!",
        "docs": "/docs",
        "example": "/stock-data/?symbol=INFY&from_date=2022-01-01&to_date=2022-01-15"
    }

@app.get("/stock-data/", response_model=List[StockData], tags=["Stock Data"])
def get_stock_data(
    symbol: str = Query(..., description="Stock symbol, e.g., INFY, TCS, RELIANCE, ICICIBANK"),
    from_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    to_date: date = Query(..., description="End date in YYYY-MM-DD format"),
    fno_only: bool = Query(False, description="Set true to restrict to F&O stocks only")
):
    import traceback
    symbol = symbol.upper()

    # Validate date range
    if from_date > to_date:
        raise HTTPException(status_code=400, detail=f"`from_date` ({from_date}) cannot be after `to_date` ({to_date})")

    if fno_only:
        fno_symbols = get_fno_symbols()
        if symbol not in fno_symbols:
            raise HTTPException(status_code=400, detail=f"{symbol} is not in the F&O stock list.")

    # Try DB cache if available
    if stock_cache:
        cached = stock_cache.find_one({
            "symbol": symbol,
            "from_date": str(from_date),
            "to_date": str(to_date)
        })
        if cached:
            try:
                return json.loads(cached["data"])
            except Exception as e:
                print("Cache decoding error:", e)

    # Fetch fresh from NSE
    try:
        df = stock_df(symbol=symbol, from_date=from_date, to_date=to_date)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol} between {from_date} and {to_date}")

        # Normalize column names
        df.columns = [col.upper() for col in df.columns]

        # Define possible column mappings
        ch_col_map = {
            "CH_TIMESTAMP": "DATE",
            "CH_OPENING_PRICE": "OPEN",
            "CH_TRADE_HIGH_PRICE": "HIGH",
            "CH_TRADE_LOW_PRICE": "LOW",
            "CH_CLOSING_PRICE": "CLOSE",
            "CH_TOT_TRADED_QTY": "VOLUME"
        }

        simple_col_map = {
            "DATE": "DATE",
            "OPEN": "OPEN",
            "HIGH": "HIGH",
            "LOW": "LOW",
            "CLOSE": "CLOSE",
            "VOLUME": "VOLUME"
        }

        # Choose appropriate mapping
        if all(col in df.columns for col in ch_col_map.keys()):
            df = df[list(ch_col_map.keys())].rename(columns=ch_col_map)
        elif all(col in df.columns for col in simple_col_map.keys()):
            df = df[list(simple_col_map.keys())]
        else:
            print(f"Returned columns from NSE for {symbol}:", df.columns.tolist())
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected data format received from NSE. Columns: {df.columns.tolist()}"
            )

        # Format and add SYMBOL
        df["DATE"] = pd.to_datetime(df["DATE"]).dt.strftime("%Y-%m-%d")
        df["SYMBOL"] = symbol

        result = df[["DATE", "SYMBOL", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]].to_dict(orient="records")

        # Save to DB cache
        if stock_cache:
            try:
                stock_cache.insert_one({
                    "symbol": symbol,
                    "from_date": str(from_date),
                    "to_date": str(to_date),
                    "data": json.dumps(result)
                })
            except Exception as e:
                print("Mongo insert error:", e)

        return result

    except ValueError as ve:
        print("Parsing error:", ve)
        raise HTTPException(status_code=500, detail=f"Data parse error from NSE for {symbol}: {ve}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching stock data: {str(e)}")



@app.get("/index-data/", response_model=List[IndexData], tags=["Index Data"])
def get_index_data(
    symbol: str = Query(..., description="Index symbol, e.g., NIFTY, BANKNIFTY"),
    from_date: date = Query(...),
    to_date: date = Query(...)
):
    symbol = symbol.upper()

    try:
        df = index_df(symbol=symbol, from_date=from_date, to_date=to_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching index data: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No index data found for {symbol} between {from_date} and {to_date}")

    df["DATE"] = df["DATE"].dt.strftime("%Y-%m-%d")
    df["SYMBOL"] = symbol
    return df[["DATE", "SYMBOL", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]].to_dict(orient="records")

@app.get("/fno-symbols/", response_model=List[str], tags=["Metadata"])
def list_fno_symbols():
    """
    Returns the list of all F&O tradable stock symbols.
    """
    return get_fno_symbols()


@app.get("/test-mongodb/", tags=["Debug"])
def test_mongodb():
    try:
        mongo_url = os.environ.get("MONGO_URL")
        print(f"🔍 MONGO_URL: {mongo_url}")  # DEBUG

        if mongo_url:
            mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            mongo_client.admin.command('ping')  # Check connection
            print("✅ MongoDB ping successful")

            db = mongo_client["jugaad_cache"]
            stock_cache = db["stock_data"]
            print("✅ MongoDB collection ready:", stock_cache.full_name)
        else:
            print("⚠️ MONGO_URL not found in environment.")
    except Exception as e:
        print("❌ MongoDB initialization failed:", e)
