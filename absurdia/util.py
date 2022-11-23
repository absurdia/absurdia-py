import io
import logging
import sys
import os
import psutil
import platform
import datetime
import calendar
import time, json, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pathlib import Path
from collections import OrderedDict

try:
    pd = __import__("pandas")
except ImportError:
    pd = None

import absurdia

dirname = os.path.dirname(__file__)
homedir = str(Path.home())
saved_agent_path = homedir + "/.absurdia/agent.env"

ABSURDIA_LOG = os.environ.get("ABSURDIA_LOG", default="warn")

logger = logging.getLogger("absurdia")

__all__ = [
    "io",
    "utf8",
    "log_info",
    "log_debug",
    "logfmt",
]

def current_timestamp(granularity="us"):
    if granularity == "us":
        return int(datetime.datetime.now().timestamp() * 1e6)
    elif granularity == "ms":
        return int(datetime.datetime.now().timestamp() * 1e3)
    elif granularity == "s":
        return int(datetime.datetime.now().timestamp())
    else:
        raise ValueError("Invalid granularity: {}".format(granularity))

def now_ms():
    return int(round(time.time() * 1000))


def to_df(obj):
    if pd is None:
        raise ImportError(
            "`pandas` is required to convert to a DataFrame. "
            "Install with `pip install pandas`"
        )
    else:
        return pd.DataFrame(obj, columns=obj[0].keys())

def utf8(value):
    return value.encode("utf-8")

def is_appengine_dev():
    return "APPENGINE_RUNTIME" in os.environ and "Dev" in os.environ.get(
        "SERVER_SOFTWARE", ""
    )

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
        absurdia.token = os.environ['ABSURDIA_TOKEN']
    if os.environ.get('ABSURDIA_SIG_KEY') is not None:
        absurdia.agent_signature_key = os.environ['ABSURDIA_SIG_KEY']
    if os.environ.get('ABSURDIA_AGENT_ID') is not None:
        absurdia.agent_id = os.environ['ABSURDIA_AGENT_ID']
    if os.path.exists(absurdia.agent_filepath) \
    and (absurdia.token is None \
    or absurdia.agent_signature_key is None \
    or absurdia.agent_id is None):
        file = open(absurdia.agent_filepath, "r").read()
        load_agent_from_filecontent(file)
    if os.path.exists(saved_agent_path) \
    and (absurdia.token is None \
    or absurdia.agent_signature_key is None \
    or absurdia.agent_id is None):
        file = open(saved_agent_path, "r").read()
        load_agent_from_filecontent(file)

def _save_agent():
    if absurdia.token is not None:
        home_agent_file = open(saved_agent_path, "w+")
        home_agent_file.write('\n'.join([
            "ABSURDIA_TOKEN=" + absurdia.token,
            "ABSURDIA_SIG_KEY=" + absurdia.agent_signature_key or "",
            "ABUSRDIA_AGENT_ID=" + absurdia.agent_id or ""
        ]))
        home_agent_file.close()

def load_agent_from_filecontent(content: str, save=False):
    idx = content.find("ABSURDIA_TOKEN")
    if idx > -1 and absurdia.token is None:
        idx = idx + (len("ABSURDIA_TOKEN") + 1)
        absurdia.token = content[idx:content.find("\n", idx)]
    idx = content.find("ABSURDIA_SIG_KEY")
    if idx > -1 and absurdia.agent_signature_key is None:
        idx = idx + (len("ABSURDIA_SIG_KEY") + 1)
        absurdia.agent_signature_key = content[idx:content.find("\n", idx)]
    idx = content.find("ABSURDIA_AGENT_ID")
    if idx > -1 and absurdia.agent_id is None:
        idx = idx + (len("ABSURDIA_AGENT_ID") + 1)
        absurdia.agent_id = content[idx:content.find("\n", idx)]
    if save and absurdia.token:
        _save_agent()

def _encode_datetime(dttime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)

def _encode_nested_dict(key, data, fmt="%s[%s]"):
    d = OrderedDict()
    for subkey, subvalue in data.items():
        d[fmt % (key, subkey)] = subvalue
    return d

def _api_encode(data):
    for key, value in data.items():
        key = utf8(key)
        if value is None:
            continue
        elif isinstance(value, list) or isinstance(value, tuple):
            for i, sv in enumerate(value):
                if isinstance(sv, dict):
                    subdict = _encode_nested_dict("%s[%d]" % (key, i), sv)
                    for k, v in _api_encode(subdict):
                        yield (k, v)
                else:
                    yield ("%s[%d]" % (key, i), utf8(sv))
        elif isinstance(value, dict):
            subdict = _encode_nested_dict(key, value)
            for subkey, subvalue in _api_encode(subdict):
                yield (subkey, subvalue)
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, utf8(value))

def dump(payload):
    return (json.dumps(payload, separators=(',', ':')) if len(payload) else '')

def sign(payload: dict = {}) -> str:
    global PRIVATE_KEY
    if PRIVATE_KEY is None:
        if absurdia.agent_signature_key:
            PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(
                base64.b64decode(absurdia.agent_signature_key)
            )
        else:
            raise RuntimeError(
                "No signature key provided. "
                "A signature key is required for endpoints that require signatures."
                )
    timestamp = int(time.time_ns() / 1000)
    payload_bytes = f"{timestamp}.{dump(payload)}".encode()
    print(payload_bytes)
    sig_raw = PRIVATE_KEY.sign(payload_bytes)
    signature = base64.urlsafe_b64encode(sig_raw).replace(b'=', b'').decode()
    return f"t={timestamp},s={signature}"

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

def get_host_info() -> dict:
    return {
        "absurdia_pkg_version": absurdia.__version__,
        "absurdia_pkg_lang": "python",
        "python_version":  sys.version,
        "hostname": platform.node(),
        "os": platform.system(),
        "arch": platform.machine(),
        "platform_version": platform.version(),
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "max_freq_mhz": psutil.cpu_freq().max
        },
        "memory_total": psutil.virtual_memory().total
    }