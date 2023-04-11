#!/usr/bin/env python3
from os import name
from time import sleep
import json
import requests
import asyncio
from pybit.unified_trading import WebSocket
from botSettings import *

def handle_message(message):
    print(message)

ws = WebSocket(
        testnet=False,
        channel_type="linear"  
)

def get_symbols():
    print("Fetching USDT symbols ...")
    response = requests.get("https://api.bybit.com/v2/public/symbols")
    response.raise_for_status()
    data = response.json()
    usdt_symbols = [symbol for symbol in data["result"] if symbol["quote_currency"] == "USDT"]
    print("Done !")
    return usdt_symbols

def get_ticker_info(symbol_name):
    response = requests.get(f"https://api.bybit.com/v2/public/tickers?symbol={symbol_name}")
    response.raise_for_status()
    return response.json()["result"][0]

def min_order_value(current_price, min_order_size):
    return current_price * min_order_size

def getCoinsToTrade(usdt_symbols):
    line = f'Only coint with a price above {TRADE_COIN_ABOVE_PRICE} USDT will be traded!'
    print(line)
    print("Fetching USDT symbols to trade ...")
    liquidationCandidates = []

    for symbol in usdt_symbols:
        ticker_info = get_ticker_info(symbol["name"])
        current_price = float(ticker_info["last_price"])
        min_order_size = float(symbol["lot_size_filter"]["min_trading_qty"])
        min_order_value_result = min_order_value(current_price, min_order_size)
        
        if min_order_value_result > TRADE_COIN_ABOVE_PRICE:
            line = f'{symbol["name"]}, {current_price}, {min_order_size}, {min_order_value_result:.6f}'
            print(line)
            liquidationCandidates.append(symbol["name"])
    print("Done !")

    return liquidationCandidates

async def subsribeLiquidations(symbol_list):
    for symbol in symbol_list:
        line = f'Subscribint to liquidation stream for {symbol}'
        print(line)
        try:
            ws.liquidation_stream(symbol, handle_message)
        except:
            print("Error subscribing to pair.")
    print("Done !")

async def main():
    usdt_symbols = get_symbols()
    await subsribeLiquidations(getCoinsToTrade(usdt_symbols))

    while True:
        sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
