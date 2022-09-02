import absurdia
import httpx

from click import echo, secho

client = httpx.Client(http2=True, base_url="https://api.absurdia.markets")

def check_login():
    absurdia.util.load_agent()
    if absurdia.agent_token is None:
        secho("No agent is logged in.", fg="red", err=True)
        echo("Use the command `absurdia login` to log an agent in.")