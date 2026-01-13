import logging
from pythonnet import load

load("coreclr")
import clr
import json
from pathlib import Path


def JSON_to_uasset(room_json: dict, room_name: str):
    # Load the assembly. The dll_path needs to be an absolute reference to libs/UAssetAPI.dll:
    dll_path = Path.cwd() / "libs" / "UAssetAPI.dll"
    clr.AddReference(str(dll_path))
    # We load the methods to read from JSON and save:
    from UAssetAPI import UAsset
    from UAssetAPI import UnrealTypes

    # DeserializeJson expects a string:
    save_path = Path("assets") / Path(f"{room_name}.uasset")
    UAsset.DeserializeJson(json.dumps(room_json)).Write(str(save_path))
    logging.info(f"Written UAsset in assets/{room_name}.uasset")
