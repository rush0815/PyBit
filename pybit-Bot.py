#!/usr/bin/env python3
from os import name
import websocket    #pip3 install websocket-client[optional]
import _thread
import time
from time import sleep
import rel
import json
import requests
import asyncio
from pybit.unified_trading import WebSocket

INTERVALL_WS_HEARTBEAT = 10

def handle_message(message):
    print(message)

def on_message(ws, message):
    result = json.loads(message)
    print(result)

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("Opened connection")

def job_ws_send_heartbeat():
    ws.send('{"op":"ping"}')

ws = WebSocket(
        testnet=False,
        channel_type="linear",
)

def get_symbols():
    response = requests.get("https://api.bybit.com/v2/public/symbols")
    response.raise_for_status()
    data = response.json()
    usdt_symbols = [symbol for symbol in data["result"] if symbol["quote_currency"] == "USDT"]
    return usdt_symbols

def get_ticker_info(symbol_name):
    response = requests.get(f"https://api.bybit.com/v2/public/tickers?symbol={symbol_name}")
    response.raise_for_status()
    return response.json()["result"][0]

def min_order_value(current_price, min_order_size):
    return current_price * min_order_size

def getCoinsToTrade(usdt_symbols):
    liquidationCandidates = []

    for symbol in usdt_symbols:
        ticker_info = get_ticker_info(symbol["name"])
        current_price = float(ticker_info["last_price"])
        min_order_size = float(symbol["lot_size_filter"]["min_trading_qty"])
        min_order_value_result = min_order_value(current_price, min_order_size)
        
        if min_order_value_result > 0.05:
            line = f'{symbol["name"]}, {current_price}, {min_order_size}, {min_order_value_result:.6f}'
            print(line)
            liquidationCandidates.append(symbol["name"])

    return liquidationCandidates

async def subsribeLiquidations(symbol_list):
    for symbol in symbol_list:
        line = f'{{\"op\":\"subscribe\",\"args\":[\"liquidation.{symbol}\"]}}'

        try:
            ws.liquidation_stream(symbol, handle_message)
        except:
            print("Error subscribing pair.")

async def main():
    usdt_symbols = get_symbols()
    await subsribeLiquidations(getCoinsToTrade(usdt_symbols))
    print("main")
    while True:
        sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
