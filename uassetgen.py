from pythonnet import load
load("coreclr")
import clr
import json
import os


def JSON_to_uasset(path: str, room_name: str):
    dll_path = os.environ.get("UASSETAPI_DLL_PATH") 
    if dll_path is None:
        raise Exception("Please set env var UASSETAPI_DLL_PATH")
    # Load the assembly:
    clr.AddReference(f"{dll_path}/libs/UAssetAPI.dll")
    # We load the methods to read from JSON and save:
    from UAssetAPI import UAsset
    from UAssetAPI import UnrealTypes

    with open(path, 'r') as f:
        j = json.load(f)
    # DeserializeJson expects a string:
    UAsset.DeserializeJson(json.dumps(j)).Write(f"assets/{room_name}_pre.uasset")
    json_string = UAsset(f"assets/{room_name}_pre.uasset", UnrealTypes.EngineVersion.VER_UE4_27).SerializeJson()
    UAsset.DeserializeJson(json_string).Write(f"assets/{room_name}.uasset")
    #with open(f"assets/{room_name}.json", 'w') as f:
    #    json.dump(json.loads(json_string), f, indent=4)


