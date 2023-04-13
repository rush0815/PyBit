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

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

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

#exchange.set_sandbox_mode(True) # activates testnet mode
#exchange.options['defaultType'] = 'swap'
markets = exchange.load_markets()

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
        line = f'Got pair {liquidation_message["data"]["symbol"]}; Side {liquidation_message["data"]["side"]}; Liquidated volume {str(volume)}'
        print(OKGREEN + line + ENDC)
        return True
    else:
        return False


def placeOrder(liquidation_message):
    liquidated_pair = liquidation_message["data"]["symbol"]
    if liquidated_pair in blacklist:
        line = f'Pair {liquidated_pair} is on blacklist!' 
        print(line)
        return
    else:
        liquidated_pair_price = liquidation_message["data"]["price"]
        liquidated_side = liquidation_message["data"]["side"]
        orderSize_percentage = float(getWalletBalance()) * float(PERCENT_ORDER_SIZE)
        order_cost = orderSize_percentage * float(liquidated_pair_price)
        
        order_pair_ccxt = liquidated_pair[ : liquidated_pair.find("USDT")] + "/USDT:USDT"
        #order = exchange.createMarketBuyOrder(order_pair_ccxt, order_cost)
        #print(order)
        if liquidated_side == 'Sell':
            order_side = "sell"
            order = exchange.createMarketSellOrder(order_pair_ccxt, order_cost)
        else:
            order_side = "buy"
            order = exchange.createMarketBuyOrder(order_pair_ccxt, order_cost)
        line = f'liquidated_price={liquidated_pair_price}\nliquidated_side = {liquidated_side}\nBalance = {getWalletBalance()}\norderSize_percentage = {orderSize_percentage}\norder_cost = {order_cost}'
        print(line)
        print (order)
        # print(session.place_order(
        #     category="linear",
        #     symbol=order_pair,
        #     side=order_side,
        #     orderType="Market",
        #     qty=str(orderSize),
        # ))
        #order = exchange.createOrder (order_pair, 'market', order_side, 1, None, {'qty': 1})
        #pprint(order)
        


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
