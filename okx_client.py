import base64
import hashlib
import hmac
import json
import time
from typing import Any

import requests


class OKXClient:
    def __init__(self, api_key: str, api_secret: str, passphrase: str, base_url: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = base_url.rstrip("/")

    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

    def _sign(self, timestamp: str, method: str, path: str, body: str) -> str:
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode()

    def _headers(self, timestamp: str, signature: str) -> dict[str, str]:
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body_text = json.dumps(body) if body else ""
        query = ""
        if params:
            query = "?" + "&".join(f"{key}={value}" for key, value in params.items())
        timestamp = self._timestamp()
        signature = self._sign(timestamp, method, f"{path}{query}", body_text)
        response = requests.request(
            method=method,
            url=f"{url}{query}",
            headers=self._headers(timestamp, signature),
            data=body_text if body else None,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "0":
            raise RuntimeError(f"OKX API error: {payload}")
        return payload

    def get_ticker(self, inst_id: str) -> float:
        payload = self._request("GET", "/api/v5/market/ticker", params={"instId": inst_id})
        return float(payload["data"][0]["last"])

    def get_candles(self, inst_id: str, bar: str, limit: int) -> list[list[str]]:
        payload = self._request("GET", "/api/v5/market/candles", params={"instId": inst_id, "bar": bar, "limit": limit})
        return payload["data"]

    def get_balance(self, ccy: str) -> float:
        payload = self._request("GET", "/api/v5/account/balance", params={"ccy": ccy})
        details = payload["data"][0].get("details", [])
        for detail in details:
            if detail.get("ccy") == ccy:
                return float(detail.get("availBal", "0"))
        return 0.0

    def place_market_order(self, inst_id: str, side: str, size: float) -> str:
        body = {
            "instId": inst_id,
            "tdMode": "cash",
            "side": side,
            "ordType": "market",
            "sz": str(size),
        }
        payload = self._request("POST", "/api/v5/trade/order", body=body)
        return payload["data"][0]["ordId"]

    def place_stop_loss_order(self, inst_id: str, side: str, trigger_price: float, size: float) -> str:
        body = {
            "instId": inst_id,
            "tdMode": "cash",
            "side": side,
            "ordType": "conditional",
            "triggerPx": str(trigger_price),
            "orderPx": "-1",
            "sz": str(size),
        }
        payload = self._request("POST", "/api/v5/trade/order-algo", body=body)
        return payload["data"][0]["algoId"]

    def cancel_algo_order(self, algo_id: str, inst_id: str) -> None:
        body = {"algoId": algo_id, "instId": inst_id}
        self._request("POST", "/api/v5/trade/cancel-algos", body=body)
