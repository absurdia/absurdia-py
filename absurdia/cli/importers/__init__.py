import subprocess
import absurdia
import click

from click import secho, echo
from absurdia.cli.common import client, check_login
from .freqtrade import bundle_results, transform_cmd

def upload_results(exportpath: str, configpath: str, name: str = None, cli_command: str = None):
    bundle = bundle_results(exportpath, configpath)
    bundle["host"] = absurdia.util.get_host_info()
    if cli_command:
        bundle["cli_command"] = cli_command
    if name:
        bundle["name"] = name
    response = client.post("/v1/strategies/import", 
        json=bundle,
        headers={
            "Authorization": "Bearer {}".format(absurdia.agent_token),
            "Accept-encoding": "gzip,br",
            "Content-Type": "application/json"
        }
    )
    if response.is_success:
        secho("Successfully imported!", fg='green')
        response_data = response.json()["data"]
        bid = response_data["id"]
        sid = response_data["strategy_id"]
        # Show page where the backtest is available
        echo("""The results are available at: 
             https://app.absurdia.markets/dash/backtesting/strategies/{}/backtests/{}
             """.format(sid, bid)
            )
    else:
        secho("Failed to import bundled results: " + response.text, fg="red", err=True)

@click.command(name="import", context_settings={"ignore_unknown_options": True})
@click.option('-n', '--name', type=str, 
              help="A name for the backtest. If not given, will be created randomly.")
@click.option('--freqtrade', nargs=0, 
              help="""A `freqtrade backtesting` command to run.
              The result of the backtest will be uploaded to Absurdia.""")
@click.option('-a', '--adapter', type=str, 
              help="Adapter to use.")
@click.option('-p', '--params', type=click.Path(exists=True, dir_okay=False), 
              help="Path to parameters/configs file (JSON).")
@click.option('-d', '--data', type=click.Path(exists=True, dir_okay=False), 
              help="Path to data file (JSON).")
@click.argument('command', nargs=-1, required=False)
def _import(name, freqtrade, adapter, params, data, command):
    """
    Backtesting service to automatically upload the results of
    a backtest once it has finished.
    Example: absurdia backtest --freqtrade backtesting
    """
    check_login()

    if isinstance(freqtrade, tuple) and command:
        cmd = ("freqtrade",) + command
        secho("[Absurdia] Running Freqtrade command: " + " ".join(cmd), fg='blue')
        fin = transform_cmd(cmd)
        process = subprocess.Popen(fin["command"])
        process.wait()
        upload_results(fin["exportpath"], fin["configpath"], name=name, cli_command=" ".join(cmd))

    elif adapter == 'freqtrade':
        if not data:
            secho("Invalid import command. Missing a `--data` argument.", fg='red', err=True)
            return
        else:
            upload_results(data, params)
    else:
        echo(click.style("Invalid import command.", fg='red'), err=True)