#!/usr/bin/env python3
from os import name
from time import sleep
import json
import requests
import asyncio
from pybit.unified_trading import WebSocket
from pybit.unified_trading import HTTP
from botSettings import *
import ccxt
from pprint import pprint

blacklist = BLACKLIST.split(",")
whitelist = []

def handle_message(message):
    if checkIfTradable(message):
        print("Placing order ...")
        placeOrder(message)
    else:
        print("Liquidated volume to low !")

ws = WebSocket(
        testnet=False,
        channel_type="linear"  
)

session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET,
)

exchange_id = 'bybit'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': API_KEY,
    'secret': API_SECRET,
})

#just a ccxt test call
ret = exchange.fetchBalance ()
print(ret['USDT'])

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
    line = f'Only coins with a price under {TRADE_COIN_MAX_ORDER_VALUE} USDT will be traded!'
    print(line)
    print("Fetching USDT symbols to trade ...")
    liquidationCandidates = []

    for symbol in usdt_symbols:
        ticker_info = get_ticker_info(symbol["name"])
        current_price = float(ticker_info["last_price"])
        min_order_size = float(symbol["lot_size_filter"]["min_trading_qty"])
        min_order_value_result = min_order_value(current_price, min_order_size)
        
        if min_order_value_result < TRADE_COIN_MAX_ORDER_VALUE:
            line = f'{symbol["name"]}, {current_price}, {min_order_size}, {min_order_value_result:.6f}'
            print(line)
            liquidationCandidates.append(symbol["name"])
    print("Done !")

    return liquidationCandidates


async def subsribeLiquidations(symbol_list):
    for symbol in symbol_list:
        line = f'Subscribing to liquidation stream for {symbol}'
        print(line)
        try:
            ws.liquidation_stream(symbol, handle_message)
        except:
            print("Error subscribing to pair.")
    print("Done !")


def checkIfTradable(liquidation_message):
    #print(liquidation_message)
    size = float(liquidation_message["data"]["size"])
    price = float(liquidation_message["data"]["price"])
    pair = liquidation_message["data"]["symbol"]
    volume = size * price
    line = f'Got liquidatino for {liquidation_message["data"]["symbol"]}; Side {liquidation_message["data"]["side"]}; Liquidated volume {str(volume)}'
    print (line)
    if (volume > MIN_LIQUIDATION_VOLUME) and (pair in whitelist):
        #line = f'Got pair {liquidation_message["data"]["symbol"]}; Side {liquidation_message["data"]["side"]}; Liquidated volume {str(volume)}'
        #print(line)
        return True
    else:
        return False


def placeOrder(liquidation_message):
    order_pair = liquidation_message["data"]["symbol"]
    if order_pair in blacklist:
        line = f'Pair {order_pair} is on blacklist!' 
        print(line)
        return
    else:
        orderSize = getWalletBalance() * PERCENT_ORDER_SIZE
        side = liquidation_message["data"]["side"]
        if side == 'Sell':
            order_side = "buy"
        else:
            order_side = "sell"

        # print(session.place_order(
        #     category="linear",
        #     symbol=order_pair,
        #     side=order_side,
        #     orderType="Market",
        #     qty=str(orderSize),
        # ))
        order = exchange.createOrder (order_pair, 'market', order_side, 1, None, {'qty': 1})
        pprint(order)
        


def getWalletBalance():
    walletInfo = session.get_wallet_balance(accountType="CONTRACT")
    return float(walletInfo["result"]["list"][0]["coin"][1]["walletBalance"])


async def main():
    walletInfo = session.get_wallet_balance(accountType="CONTRACT")
    walletBalance = walletInfo["result"]["list"][0]["coin"][1]["walletBalance"]
    equity = walletInfo["result"]["list"][0]["coin"][1]["equity"]
    totalPositionIM = walletInfo["result"]["list"][0]["coin"][1]["totalPositionIM"]
    unrealisedPnl = walletInfo["result"]["list"][0]["coin"][1]["unrealisedPnl"]
    cumRealisedPnl = walletInfo["result"]["list"][0]["coin"][1]["cumRealisedPnl"]
    line = f'Balance: {walletBalance}\nEquity: {equity}\nuPnL: {unrealisedPnl}\ncum PnL:{cumRealisedPnl}'
    print(line)
    
    usdt_symbols = get_symbols()
    global whitelist
    whitelist = getCoinsToTrade(usdt_symbols)

    await subsribeLiquidations(whitelist)

    while True:
        sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
