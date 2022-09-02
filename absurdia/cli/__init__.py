import os
import absurdia
import click

from click import echo, secho

from .common import client
from .importers import _import

os.environ['ABSURDIA_BACKTEST'] = '1'

def validate_token(ctx, param, value):
    if value:
        if len(value) != 64:
            raise click.BadParameter("Invalid agent token.")
    return value

@click.group()
def cli():
    return

@cli.command()
@click.option('--save/--no-save', default=True, help="Print verbose log messages.")
@click.option('-f','--file', type=click.File('rb'), help="""
              Agent credentials file (downloaded from your dashboard).""")
@click.option('-t','--token', type=str, callback=validate_token, help="Agent token.")
@click.option('-s','--sig-key', type=str, help="Agent signature key.")
def login(save, file, token, sig_key):
    """
    Set an API credentials of one of your agent to interact with Absurdia.
    Example: absurdia login --token abcdefghijklmnopqrstuvwxyz0123456789
            --sig-key abcdefghijklmnopqrstuvwxyz0123456789
    """
    
    if not (file or token):
        secho("One of --file or --token must be specified.", fg='red')
        return
    
    if token:
        os.environ['ABSURDIA_TOKEN'] = token
        absurdia.agent_token = token
        if sig_key:
            os.environ['ABSURDIA_SIG_KEY'] = sig_key
            absurdia.agent_signature_key = sig_key        
    elif file:
        absurdia.util.load_agent_from_filecontent(file.read())
    
    # Test we can get the agent's data
    agent_resp = client.get("/v1/agents/{}".format(absurdia.agent_token), headers={
        "Authorization": "Bearer {}".format(absurdia.agent_token)
    })
    if agent_resp.is_success:
        agent = agent_resp.json()['data']
        secho("Successfully logged agent {} in.".format(agent['name']), fg='green')
        if save:
            absurdia.util._save_agent()
    else:
        secho("Failed to log in with given credentials. API Response: {}".format(agent_resp.text), fg='red')
        

cli.add_command(login)
cli.add_command(_import)
