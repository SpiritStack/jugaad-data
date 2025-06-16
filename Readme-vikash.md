# Jugaad Data API (FastAPI on Render)

A simple REST API wrapper for the [`jugaad-data`](https://github.com/jugaad-py/jugaad-data) NSE data library using FastAPI.

jugaad-api/
├── main.py
├── requirements.txt
├── render.yaml
└── README.md



## 🚀 Endpoints

- `/symbols/stocks`
- `/symbols/indexes`
- `/stock-data?symbol=RELIANCE&start=2023-01-01&end=2023-12-31`
- `/index-data?symbol=NIFTY%2050&start=2023-01-01&end=2023-12-31`
- `/fo/expiry-dates`
- `/fo/option-chain?symbol=RELIANCE&expiry=2025-06-26`

## 🛠 Deployment (Render)

1. Push this project to your GitHub repo.
2. Go to [https://dashboard.render.com](https://dashboard.render.com)
3. Click **New > Web Service**
4. Connect GitHub and select your repo.
5. Render will detect `render.yaml` and auto-configure everything.
6. Hit **Deploy**. Done!

## 🔗 Swagger Docs

Once deployed, go to: `https://your-app-name.onrender.com/docs`


