# Official Absurdia Bindings for Python
![PyPI](https://img.shields.io/pypi/v/absurdia?style=flat-square)

A Python library for Absurdia's API.

## Install

You can install this package by using the pip tool and installing:

    $ pip install absurdia


## Signing up to Absurdia backtesting

Sign up for Absurdia at https://app.absurdia.markets/signup.

## Using the the package

Create a new agent in (your dashboard)[https://app.absurdia.markets/agents] and 
download the credential file. Use the agent token with the client as in the example blow.

```python
from absurdia import Client

# Create client
client = Client('<Your Agent Token>')

# Get your account
account = client.accounts.current()
```

Alternatively, use the environment variable `ABSURDIA_TOKEN`, or put the credential file in the same directory as your Python script.

## Import a Freqtrade backtest

Freqtrade backtests are run using its CLI. This Python library also comes with a CLI that can work together with Freqtrade's commands. First, add a token to authenticate your agent:

```shell
$ absurdia login --token '<Your Agent Token>'
```

Once authenicated, simply append `absurdia backtest --` to your Freqtrade backtesting command. For example:

```shell
$ absurdia backtest --freqtrade backtesting --strategy AwesomeStrategy --timeframe 1m
```

## License

Licensed under the BSD 3 license, see [LICENSE](LICENSE).