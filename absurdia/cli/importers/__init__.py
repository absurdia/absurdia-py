import subprocess
import absurdia
import click

from click import secho, echo
from absurdia.cli.common import check_login
from .freqtrade import read_results, transform_cmd

def upload_freqtrade_results(exportpath: str, 
                             configpath: str, 
                             name: str = None, 
                             cli_command: str = None):
    """Uploads Freqtrade results to Absurdia"""

    data = read_results(exportpath, configpath)
    client = absurdia.Client(agent=absurdia.token)
    
    try:
        backtest = client.backtests.import_freqtrade(data, name, cli_command)
        secho("Successfully imported!", fg='green')
        bid = backtest["id"]
        sid = backtest["strategy_id"]
        # Show page where the backtest is available
        echo("""The results are available at: 
             https://app.absurdia.markets/backtesting/strategies/{}/backtests/{}
             """.format(sid, bid)
        )
    except Exception as e:
        secho("Failed to upload backtest. %s" % (e,), fg="red", err=True)

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
        upload_freqtrade_results(
            fin["exportpath"], 
            fin["configpath"], 
            name=name, 
            cli_command=" ".join(cmd)
        )
    elif adapter == 'freqtrade':
        if not data:
            secho(
                "Invalid import command. Missing a `--data` argument.", 
                fg='red', 
                err=True
            )
            return
        else:
            upload_freqtrade_results(data, params)
    else:
        echo(click.style("Invalid import command.", fg='red'), err=True)