#!/usr/bin/env python3
from os import name
import websocket    #pip3 install websocket-client[optional]
import _thread
import time
import rel
import json
import requests
import asyncio



def on_message(ws, message):
    result = json.loads(message)
    print(result)

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("Opened connection")

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
            #print(symbol["name"])
            line = f'{symbol["name"]}, {current_price}, {min_order_size}, {min_order_value_result:.6f}'
            print(line)
            liquidationCandidates.append(symbol["name"])

    return liquidationCandidates

async def subsribeLiquidations(symbol_list):
    for symbol in symbol_list:
        line = f'{{\"op\":\"subscribe\",\"args\":[\"liquidation.{symbol}\"]}}'

        try:
            await ws.send(line)
        #    await ws.send('{"op":"subscribe","args":["liquidation.NKNUSDT"]}')
        except:
            print("Error subscribing pair.")

async def main():
    usdt_symbols = get_symbols()
    await subsribeLiquidations(getCoinsToTrade(usdt_symbols))
    print("main")
   

if __name__ == '__main__':
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp("wss://stream.bybit.com/v5/public/linear",
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

    ws.run_forever(dispatcher=rel, reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
    #ws.send('{"op":"subscribe","args":["liquidation.NKNUSDT"]}')
    asyncio.run(main())
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()
    
    