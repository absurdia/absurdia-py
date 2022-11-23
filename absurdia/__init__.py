# Absurdia Python bindings

from absurdia.resources import *  # noqa
from absurdia.version import VERSION
from absurdia.clients import Client
from absurdia.agent_credentials import (
    token, 
    agent_filepath, 
    agent_id, 
    agent_signature_key
)

__all__ = [
    Client,
    token,
    agent_filepath,
    agent_id,
    agent_signature_key
]

# Configuration variables

default_http_client = None
app_info = None
enable_telemetry = True
max_network_retries = 5

# Set to either 'WARNING', 'INFO', 'DEBUG'
log = 'WARNING'

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