import logging
import requests
from flask import Flask, jsonify
import os
import multiprocessing
from gunicorn.app.base import BaseApplication
import time

# --- حافظه‌ی موقت برای جلوگیری از درخواست زیاد به Nobitex ---
_cache = {}
CACHE_TTL = 3  # زمان اعتبار کش (۳ ثانیه)

def get_orderbook_from_nobitex(symbol):
    """گرفتن دفتر سفارش از API نوبیتکس با کشِ زمان‌دار"""
    cache_key = symbol
    now = time.time()

    # بررسی کش
    if cache_key in _cache:
        data, timestamp = _cache[cache_key]
        if now - timestamp < CACHE_TTL:
            logging.info(f"Cache hit برای {symbol}")
            return data

    # دریافت داده‌ی جدید از Nobitex
    url = f"https://api.nobitex.ir/v2/orderbook/{symbol}"
    try:
        logging.info(f"Fetch تازه برای {symbol}")
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        _cache[cache_key] = (data, now)
        return data
    except Exception as e:
        logging.error(f"خطا هنگام ارتباط با Nobitex: {e}")
        return {"status": "error", "message": str(e)}, 500


# --- تنظیم Flask ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/')
def home():
    return "✅ Nobitex Mirror در حال اجراست (embedded gunicorn).", 200


@app.route('/api/orderbook/<symbol>')
def orderbook(symbol):
    data = get_orderbook_from_nobitex(symbol.upper())
    if isinstance(data, tuple):
        return jsonify(data[0]), data[1]
    return jsonify(data)


# --- اجرای داخلی Gunicorn ---
class StandaloneApplication(BaseApplication):
    def __init__(self, app, opts=None):
        self.application = app
        self.options = opts or {}
        super().__init__()

    def load_config(self):
        for k, v in self.options.items():
            if k in self.cfg.settings and v is not None:
                self.cfg.set(k.lower(), v)

    def load(self):
        return self.application


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    opts = {
        "bind": f"0.0.0.0:{port}",
        "workers": (multiprocessing.cpu_count() * 2) + 1,
        "timeout": 120,
    }
    logging.info(f"🚀 اجرای Gunicorn داخلی در پورت {port}")
    StandaloneApplication(app, opts).run()
