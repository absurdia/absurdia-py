import absurdia
from click import echo, secho

def check_login():
    absurdia.util.load_agent()
    if absurdia.token is None:
        secho("No agent is logged in.", fg="red", err=True)
        echo("Use the command `absurdia login` to log an agent in.")