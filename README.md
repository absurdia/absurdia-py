# Official Absurdia Bindings for Python
=====================================

A Python library for Absurdia's API.

Supported services:
- Realtime prices (`GET /prices`)
- Realtime trades (`GET /trades`)
- Realtime orderbooks (`GET /orderbooks`)

Additional endpoints:
- Get your account (`GET /accounts`)
- Get your agents (`GET /agents`)
- Get your funds (`GET /funds`)

## Setup

You can install this package by using the pip tool and installing:

    $ pip install absurdia


## Setting up an Absurdia account

Sign up for Absurdia at https://app.absurdia.com/signup.

## Using the the package

Create a new agent in (your dashboard)[https://app.absurdia.com/dash/agents] and 
download the credential file. Put the credential file in the same directory as your Python script.

Once done, you can use the package like this:

```python
    from absurdia import markets
    import absurdia

    # Get all the supported symbols
    symbols = markets.symbols()

    # Get the price of a symbol
    price = markets.price("BTC.USDT-SPOT-BIN")

    # Get the latest 100 trades of a symbol
    trades = markets.trades("BTC.USDT-SPOT-BIN")

    # Get the latest limit order book snapshot of a symbol
    orderbook = markets.orderbook("BTC.USDT-SPOT-BIN")

    # Get your account
    account = absurdia.Account.current()
```

#### Change the path of the credentials file

You can change the path of the file with:

```python
    import absurdia

    absurdia.agent_filepath = "/path/to/file/absurdia-agent.env"
```

#### Use your credentials directly

Add the credentials the way you prefer by changing the global variables:

```python
    import absurdia

    absurdia.agent_id = "<ID>"
    absurdia.agent_token = "<Agent Token>"
    absurdia.agent_signature_key = "<Signature Key>"
```