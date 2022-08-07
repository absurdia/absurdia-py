import imp
import os

# Absurdia Python bindings

# Configuration variables

agent_filepath = "absurdia-agent.env"
agent_id = None
agent_token = None
agent_signature_key = None
default_fund = None
api_base = "https://api.absurdia.markets"
download_api_base = "https://data.absurdia.markets"
api_version = "v1"
verify_ssl_certs = True
proxy = None
default_http_client = None
app_info = None
enable_telemetry = True
max_network_retries = 0
ca_bundle_path = os.path.join(
    os.path.dirname(__file__), "data", "ca-certificates.crt"
)

# Set to either 'debug' or 'info', controls console logging
log = None

# API resources
from absurdia.api_resources import *  # noqa
from absurdia.markets import *  # noqa
from absurdia.version import VERSION

__version__ = VERSION

# Takes a name and optional version and plugin URL.
def set_app_info(name, partner_id=None, url=None, version=None):
    global app_info
    app_info = {
        "name": name,
        "partner_id": partner_id,
        "url": url,
        "version": version,
    }