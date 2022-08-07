# Official Absurdia Bindings for Python
![PyPI](https://img.shields.io/pypi/v/absurdia?style=flat-square)

A Python library for Absurdia's API.

Orders management:
- Create a new order (`POST /orders`)
- Fill an order (`POST /orders/:order_id/fill`)
- Cancel an order (`POST /orders/:order_id/cancel`)
- Reject an order (`POST /orders/:order_id/reject`)
- Get and order (`GET /orders/:order_id`)

Additional endpoints:
- Get your account (`GET /accounts`)
- Get your agents (`GET /agents`)
- Get your funds (`GET /funds`)

## Setup

You can install this package by using the pip tool and installing:

    $ pip install absurdia


## Setting up an Absurdia account

Sign up for Absurdia at https://app.absurdia.markets/signup.

## Using the the package

Create a new agent in (your dashboard)[https://app.absurdia.markets/dash/agents] and 
download the credential file. Put the credential file in the same directory as your Python script.

Once done, you can use the package like this:

```python
import absurdia

# Get your account
account = absurdia.Account.current()

# Create an order
order = absurdia.Order.create(
    fund_id="<fund_id>", 
    venue="binance", 
    venue_symbol="BTCBUSD",
    side="buy",
    quantity=0.112
)

# Get an order
order = absurdia.Order.retrieve("<order id>")

# Register an order as cancelled
order.cancel(at = absurdia.util.current_timestamp())
```

## How to load an agent's credentials

#### Option 1 - Change the path of the credentials file

When you create an agent via [your dashboard](https://app.absurdia.markets/dash/agents), you will be able to download a credential file which will contain all the variables for the SDK. Download the file and simply set the path of the file with:

```python
import absurdia

absurdia.agent_filepath = "/path/to/file/absurdia-agent.env"
```

#### Option 2 - Use your credentials directly

Add the credentials manually in your script the way you prefer by changing the global variables:

```python
import absurdia

absurdia.agent_id = "<ID>"
absurdia.agent_token = "<Agent Token>"
absurdia.agent_signature_key = "<Signature Key>"
```

#### Option 3 - Use environment variables

The environment variables must be named `ABSURDIA_TOKEN` for the agent's token, `ABSURDIA_SIG_KEY` for the agent's signature key and `ABUSRDIA_AGENT_ID` for the agent's ID. At the start of your script, the SDK will automatically detect those variables and use them as default values.

```bash
$ export ABSURDIA_TOKEN="<Agent Token>"
$ export ABSURDIA_SIG_KEY="<Signature Key>"
```

This method is the preferred method if you run your script in a hosted environment.

## License

Licensed under the BSD 3 license, see [LICENSE](LICENSE).