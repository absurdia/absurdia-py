import functools
import io
import logging
import sys
import os
import re
import datetime
from urllib.parse import quote_plus

try:
    pd = __import__("pandas")
except ImportError:
    pd = None

import absurdia

ABSURDIA_LOG = os.environ.get("ABSURDIA_LOG", default="warn")

logger = logging.getLogger("absurdia")

__all__ = [
    "io",
    "utf8",
    "log_info",
    "log_debug",
    "dashboard_link",
    "logfmt",
]

SUPPORTED_ASSETS = [
    "BTC",
    "ETH",
    "BUSD",
    "USDT",
    "USDC",
    "USD",
    "EUR",
    "GBP",
    "CHF"
]

SUPPORTED_MARKET_TYPES = ["SPOT"]

SUPPORTED_VENUES = ["BIN", "FTX", "BPD"]

def current_timestamp(granularity="us"):
    if granularity == "us":
        return int(datetime.datetime.now().timestamp() * 1e6)
    elif granularity == "ms":
        return int(datetime.datetime.now().timestamp() * 1e3)
    elif granularity == "s":
        return int(datetime.datetime.now().timestamp())
    else:
        raise ValueError("Invalid granularity: {}".format(granularity))

def to_df(obj):
    if pd is None:
        raise ImportError("`pandas` is required to convert to a DataFrame. Install with `pip install pandas`")
    else:
        return pd.DataFrame(obj, columns=obj[0].keys())

def utf8(value):
    return value.encode("utf-8")

def is_appengine_dev():
    return "APPENGINE_RUNTIME" in os.environ and "Dev" in os.environ.get(
        "SERVER_SOFTWARE", ""
    )

def get_object_classes():
    # This is here to avoid a circular dependency
    from absurdia.object_classes import OBJECT_CLASSES

    return OBJECT_CLASSES

def _console_log_level():
    if absurdia.log in ["debug", "info"]:
        return absurdia.log
    elif ABSURDIA_LOG in ["debug", "info"]:
        return ABSURDIA_LOG
    else:
        return None


def log_debug(message, **params):
    msg = logfmt(dict(message=message, **params))
    if _console_log_level() == "debug":
        print(msg, file=sys.stderr)
    logger.debug(msg)


def log_info(message, **params):
    msg = logfmt(dict(message=message, **params))
    if _console_log_level() in ["debug", "info"]:
        print(msg, file=sys.stderr)
    logger.info(msg)

def logfmt(props):
    def fmt(key, val):
        return u"{key}={val}".format(key=str(key), val=str(val))

    return u" ".join([fmt(key, val) for key, val in sorted(props.items())])

# Load agent credentials
def load_agent():
    if os.environ.get('ABSURDIA_TOKEN') is not None:
        absurdia.agent_token = os.environ['ABSURDIA_TOKEN']
    if os.environ.get('ABSURDIA_SIG_KEY') is not None:
        absurdia.agent_signature_key = os.environ['ABSURDIA_SIG_KEY']
    if os.environ.get('ABSURDIA_AGENT_ID') is not None:
        absurdia.agent_id = os.environ['ABSURDIA_AGENT_ID']
    if os.path.exists(absurdia.agent_filepath) \
    and (absurdia.agent_token is None \
    or absurdia.agent_signature_key is None \
    or absurdia.agent_id is None):
        file = open(absurdia.agent_filepath, "r").read()
        idx = file.find("ABSURDIA_TOKEN")
        if idx > -1 and absurdia.agent_token is None:
            idx = idx + (len("ABSURDIA_TOKEN") + 1)
            absurdia.agent_token = file[idx:file.find("\n", idx)]
        idx = file.find("ABSURDIA_SIG_KEY")
        if idx > -1 and absurdia.agent_signature_key is None:
            idx = idx + (len("ABSURDIA_SIG_KEY") + 1)
            absurdia.agent_signature_key = file[idx:file.find("\n", idx)]
        idx = file.find("ABSURDIA_AGENT_ID")
        if idx > -1 and absurdia.agent_id is None:
            idx = idx + (len("ABSURDIA_AGENT_ID") + 1)
            absurdia.agent_id = file[idx:file.find("\n", idx)]

def convert_to_absurdia_object(
    resp, agent_token=None, absurdia_version=None, absurdia_account=None, klass_name=None
):
    # If we get a AbsurdiaResponse, we'll want to return a
    # AbsurdiaObject with the last_response field filled out with
    # the raw API response information
    absurdia_response = None

    if isinstance(resp, absurdia.absurdia_response.AbsurdiaResponse):
        absurdia_response = resp
        resp = absurdia_response.data

    if isinstance(resp, list):
        return list([
            convert_to_absurdia_object(
                i, agent_token, absurdia_version, absurdia_account, klass_name
            )
            for i in resp
        ])
    elif isinstance(resp, dict) and not isinstance(
        resp, absurdia.absurdia_object.AbsurdiaObject
    ):
        resp = resp.copy()
        klass_name = resp.get("object") if klass_name is None else klass_name 
        if isinstance(klass_name, str):
            klass = get_object_classes().get(
                klass_name, absurdia.absurdia_object.AbsurdiaObject
            )
        else:
            klass = absurdia.absurdia_object.AbsurdiaObject

        return klass.construct_from(
            resp,
            agent_token,
            absurdia_version=absurdia_version,
            absurdia_account=absurdia_account,
            last_response=absurdia_response,
        )
    else:
        return resp

def convert_to_dict(obj):
    """Converts a AbsurdiaObject back to a regular dict.
    Nested AbsurdiaObject are also converted back to regular dicts.
    :param obj: The AbsurdiaObject to convert.
    :returns: The AbsurdiaObject as a dict.
    """
    if isinstance(obj, list):
        return [convert_to_dict(i) for i in obj]
    # This works by virtue of the fact that AbsurdiaObject _are_ dicts. The dict
    # comprehension returns a regular dict and recursively applies the
    # conversion to each value.
    elif isinstance(obj, dict):
        return {k: convert_to_dict(v) for k, v in iter(obj)}
    else:
        return obj


def populate_headers(idempotency_key):
    if idempotency_key is not None:
        return {"Idempotency-Key": idempotency_key}
    return None


def merge_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


def sanitize_id(id):
    utf8id = utf8(id)
    quotedId = quote_plus(utf8id)
    return quotedId


class class_method_variant(object):
    def __init__(self, class_method_name):
        self.class_method_name = class_method_name

    def __call__(self, method):
        self.method = method
        return self

    def __get__(self, obj, objtype=None):
        @functools.wraps(self.method)
        def _wrapper(*args, **kwargs):
            if obj is not None:
                # Method was called as an instance method, e.g.
                # instance.method(...)
                return self.method(obj, *args, **kwargs)
            elif len(args) > 0 and isinstance(args[0], objtype):
                # Method was called as a class method with the instance as the
                # first argument, e.g. Class.method(instance, ...) which in
                # Python is the same thing as calling an instance method
                return self.method(args[0], *args[1:], **kwargs)
            else:
                # Method was called as a class method, e.g. Class.method(...)
                class_method = getattr(objtype, self.class_method_name)
                return class_method(*args, **kwargs)

        return _wrapper

def validate_symbol(symbol: str) -> bool:
    symbol = symbol.upper()
    parts = symbol.split("-")
    if len(parts) < 2:
        return False
    elif len(parts) == 2:
        venue = None
    elif len(parts) == 3:
        venue = parts[2]
    assets = parts[0].split(".")
    market_type = parts[1]

    if len(assets) < 2:
        return False
    base = assets[0]
    quote = assets[1]
    if base == quote:
        return False

    if not base in SUPPORTED_ASSETS or not quote in SUPPORTED_ASSETS:
        return False
    
    if not market_type in SUPPORTED_MARKET_TYPES:
        return False

    if not venue in SUPPORTED_VENUES:
        return False

    return True

def compose_symbol(base: str, quote: str, market_type: str, venue: str) -> str:
    base = base.upper()
    quote = quote.upper()
    market_type = market_type.upper()
    venue = venue.upper()
    if not base in SUPPORTED_ASSETS or not quote in SUPPORTED_ASSETS:
        return ""
    if not market_type in SUPPORTED_MARKET_TYPES:
        return ""
    if not venue in SUPPORTED_VENUES:
        return ""
    return "{base}.{quote}-{market_type}-{venue}".format(base, quote, market_type, venue)