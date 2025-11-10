# -*- coding: utf-8 -*-
import requests
import time
import logging
from flask import Flask, jsonify
from functools import lru_cache

# =====================================================================================
# CONFIGURATION (تنظیمات مرکزی)
# =====================================================================================
# در این بخش، تمام مقادیر قابل تنظیم در یک مکان جمع شده‌اند.
# -------------------------------------------------------------------------------------
NOBITEX_API_URL = "https://api.nobitex.ir/v2/orderbook/BTCUSDT"
REQUEST_TIMEOUT = 10  # زمان انتظار برای پاسخ از نوبیتکس (به ثانیه)
CACHE_TTL_SECONDS = 3  # عمر داده‌های کش شده (به ثانیه)
USER_AGENT = "NEX-Maker-Mirror/2.0 (Production)" # هویت سرور شما در درخواست‌ها

# =====================================================================================
# LOGGING SETUP (تنظیمات لاگ‌گیری)
# =====================================================================================
# به جای print، از یک سیستم لاگ‌گیری استاندارد استفاده می‌کنیم.
# این لاگ‌ها در محیط Render قابل مشاهده خواهند بود و به عیب‌یابی کمک می‌کنند.
# -------------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =====================================================================================
# FLASK APPLICATION INITIALIZATION (ایجاد اپلیکیشن فلسک)
# =====================================================================================
app = Flask(__name__)

# =====================================================================================
# CACHING & DATA FETCHING LOGIC (منطق کش و دریافت داده)
# =====================================================================================
# این ترفند ttl_hash یک روش استاندارد و بهینه برای ایجاد کش با زمان انقضا است.
# هر `CACHE_TTL_SECONDS` ثانیه، یک مقدار جدید تولید می‌کند و lru_cache را مجبور به فراخوانی مجدد تابع می‌کند.
def get_ttl_hash(seconds=CACHE_TTL_SECONDS):
    """یک هش زمانی برای کنترل انقضای کش lru_cache برمی‌گرداند."""
    return round(time.time() / seconds)

@lru_cache(maxsize=2)
def fetch_from_nobitex(ttl_hash=None):
    """
    داده‌ها را از API نوبیتکس واکشی می‌کند.
    این تابع به صورت خودکار نتایج را کش می‌کند.
    پارامتر ttl_hash صرفاً برای کنترل زمان انقضای کش استفاده می‌شود و مقدارش مهم نیست.
    """
    logging.info("Cache expired or empty. Fetching new data from Nobitex...")
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(NOBITEX_API_URL, timeout=REQUEST_TIMEOUT, headers=headers)
        response.raise_for_status()  # اگر کد وضعیت خطا بود (مثلا 4xx یا 5xx)، استثنا پرتاب می‌کند
        logging.info("Successfully fetched new data from Nobitex.")
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"Nobitex API returned an HTTP error: {e}")
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Failed to connect to Nobitex API (Connection Error): {e}")
    except requests.exceptions.Timeout:
        logging.error(f"Request to Nobitex API timed out after {REQUEST_TIMEOUT} seconds.")
    except requests.exceptions.RequestException as e:
        logging.error(f"An unexpected error occurred while requesting data from Nobitex: {e}")
    
    return None # در صورت بروز هرگونه خطا، None برمی‌گرداند

# =====================================================================================
# API ENDPOINTS (روت‌های برنامه)
# =====================================================================================
@app.route('/')
def health_check():
    """یک روت ساده برای چک کردن سلامت و فعال بودن سرور."""
    return "Nobitex Mirror Service is healthy and running.", 200

@app.route('/api/orderbook/BTCUSDT', methods=['GET'])
def get_orderbook():
    """
    این Endpoint اصلی است که ربات شما با آن ارتباط برقرار می‌کند.
    داده‌ها را از کش یا مستقیماً از نوبیتکس (در صورت انقضای کش) برمی‌گرداند.
    """
    logging.info(f"Received a request for orderbook data.")
    
    # تابع واکشی داده را با هش زمانی جدید فراخوانی می‌کنیم تا کش به درستی کار کند
    data = fetch_from_nobitex(ttl_hash=get_ttl_hash())
    
    if data:
        return jsonify(data)
    else:
        # اگر تابع fetch_from_nobitex به دلیل خطا مقدار None برگرداند،
        # یک پاسخ خطای مناسب به کلاینت (ربات شما) ارسال می‌شود.
        error_response = {
            "status": "error",
            "message": "Upstream error: Failed to fetch data from the Nobitex API."
        }
        return jsonify(error_response), 502  # 502 Bad Gateway

# =====================================================================================
# LOCAL DEVELOPMENT SERVER (برای اجرای محلی جهت تست)
# =====================================================================================
# این بخش در محیط پروداکشن Render اجرا **نمی‌شود**.
# Gunicorn مستقیماً متغیر `app` را پیدا کرده و برنامه را از آن طریق اجرا می‌کند.
# این بلوک کد فقط برای راحتی شما در تست روی سیستم شخصی‌تان قرار داده شده است.
# -------------------------------------------------------------------------------------
if __name__ == '__main__':
    logging.info("Starting Flask development server for local testing...")
    app.run(host='0.0.0.0', port=5001, debug=False)
