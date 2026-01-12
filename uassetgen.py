import logging
from pythonnet import load

load("coreclr")
import clr
import os
import json
from pathlib import Path


def JSON_to_uasset(room_json: dict, room_name: str):
    dll_path = os.environ.get("UASSETAPI_DLL_PATH")
    if dll_path is None:
        raise Exception("Please set env var UASSETAPI_DLL_PATH")
    # Load the assembly:
    clr.AddReference(f"{dll_path}/libs/UAssetAPI.dll")
    # We load the methods to read from JSON and save:
    from UAssetAPI import UAsset
    from UAssetAPI import UnrealTypes

    # DeserializeJson expects a string:
    UAsset.DeserializeJson(json.dumps(room_json)).Write(f"assets/{room_name}.uasset")
    logging.info(f"Written UAsset in assets/{room_name}.uasset")
