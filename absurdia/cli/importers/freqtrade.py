import os
import time
import json

def transform_cmd(cmd: tuple) -> dict:
    """Returns a dictionary with new command and metadata to import.
    return {
        command: dict,
        configpath: string (file path) or None,
        exportpath: string (file path)
    }
    """
    new_cmd = list(cmd)
    result = {
        "exportpath": None,
        "configpath": None,
    }
    for i, e in enumerate(cmd):
        if e == "-c" or e.startswith("--config"):
            if len(e.split("=")) > 1:
                result["configpath"] = e.split("=")[1]
            else:
                result["configpath"] = cmd[i+1]
        if e.startswith("--export-filename"):
            if len(e.split("=")) > 1:
                result["exportpath"] = e.split("=")[1]
            else:
                result["exportpath"] = cmd[i+1]
        if e.startswith("--export"): # Force export of trades if set to anything else
            if len(e.split("=")) > 1:
                new_cmd[i+1] = "trades"

    if result["exportpath"] is None: # No export path specified
        result["exportpath"] = "backtest_{}".format(str(round(time.time())))
        new_cmd.append("--export-filename={}.json".format(result["exportpath"]))
        
    if result["configpath"] is None: # No config path specified
        result["configpath"] = "./user_data/config.json"
    
    result["command"] = new_cmd
    return result

def bundle_results(exportpath: str, configpath: str) -> dict:
    """Bundle the results into a dictionary"""
    result = { "adapter": "freqtrade" }

    import freqtrade
    result["framework"] = {
        "name" : "freqtrade",
        "version": freqtrade.__version__
    }
    
    for file in os.listdir("."):
        if file.startswith(exportpath):
            if file.endswith(".meta.json"):
                continue
            elif file.endswith(".json"):
                with open(file, "r") as f:
                    exported = json.load(f)
                    result["data"] = exported
    
    return result
