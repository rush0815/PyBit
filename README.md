# PyBit
This is my attempt to create a crypto trading bot for python.
Inspired by CryptoGnome's ByBit Lickhunter, trading strategy will be based on bybit liquidation data, RSI and MACD.

pybit-Bot.py
This file uses the pybit python module to fetch liquidation data.

If you get the error "TypeError: 'type' object is not subscribable" do the following
1. open /usr/local/lib/python3.8/dist-packages/pybit/_http_manager.py
2. go to line 39
3. change
retry_codes: defaultdict[dict] = field(
        default_factory=lambda: {},
        init=False,
    )

to

retry_codes: defaultdict(dict) = field(
        default_factory=lambda: {},
        init=False,
    )

4. save !