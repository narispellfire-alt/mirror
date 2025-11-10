# -*- coding: utf-8 -*-
"""
Mirror Server with embedded Gunicorn launcher.
"""
import os
import requests
from flask import Flask, jsonify
from gunicorn.app.base import BaseApplication

app = Flask(__name__)

CACHE = {}
TTL = 3.0  # مدت کش بین درخواست‌ها (ثانیه)

@app.route("/api/orderbook/<symbol>", methods=["GET"])
def orderbook(symbol: str):
    import time
    now = time.time()
    if symbol in CACHE and now - CACHE[symbol]["time"] < TTL:
        return jsonify(CACHE[symbol]["data"])
    try:
        res = requests.get(f"https://api.nobitex.ir/v2/orderbook/{symbol}")
        data = res.json()
        CACHE[symbol] = {"time": now, "data": data}
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


class StandaloneApplication(BaseApplication):
    """اجرای داخلی گانیکورن (self-contained)"""

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        cfg = self.cfg
        for key, value in self.options.items():
            cfg.set(key, value)

    def load(self):
        return self.application


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    options = {
        "bind": f"0.0.0.0:{port}",
        "workers": 2,
        "timeout": 60,
    }
    StandaloneApplication(app, options).run()
