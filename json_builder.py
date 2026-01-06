from collections import namedtuple
import copy
import json

from uassetgen import JSON_to_uasset

Hemisphere = namedtuple("Hemisphere", ["center", "radius", "height"])
Entrance = namedtuple("Entrance", ["location", "entrance_type", "orientation"])


def generate_floodfill(df, dr, fflines, num, outer_index):
    points = []
    new_ffill = copy.deepcopy(df)
    for point in fflines:
        x, y, z = [i if i != 0 else 0.01 for i in point.center]
        radius, height = float(point.radius), float(point.height)
        new_point = copy.deepcopy(dr)
        new_point["Value"][0]["Value"][0]["Value"]["X"] = x
        new_point["Value"][0]["Value"][0]["Value"]["Y"] = y
        new_point["Value"][0]["Value"][0]["Value"]["Z"] = z
        new_point["Value"][1]["Value"] = radius
        new_point["Value"][2]["Value"] = height
        points.append(new_point)
    new_ffill["Data"][0]["Value"] = points
    new_ffill["ObjectName"] = f"FloodFillLine_{num}"
    new_ffill["OuterIndex"] = outer_index
    new_ffill["CreateBeforeCreateDependencies"] = [outer_index]
    return new_ffill


def generate_entrance(de, entrance, num, outer_index):
    x, y, z = [i if i != 0 else 0.01 for i in entrance.location]
    roll, pitch, yaw = [i if i != 0 else 0.01 for i in entrance.orientation]
    new_entrance = copy.deepcopy(de)
    new_entrance["Data"][0]["Value"][0]["Value"]["X"] = x
    new_entrance["Data"][0]["Value"][0]["Value"]["Y"] = y
    new_entrance["Data"][0]["Value"][0]["Value"]["Z"] = z
    new_entrance["Data"][1]["Value"][0]["Value"]["Pitch"] = pitch
    new_entrance["Data"][1]["Value"][0]["Value"]["Yaw"] = yaw
    new_entrance["Data"][1]["Value"][0]["Value"]["Roll"] = roll
    match entrance.entrance_type:
        case "Exit":
            entrance_type = "ECaveEntranceType::Exit"
        case "Entrance":
            entrance_type = "ECaveEntranceType::Entrance"
        case "Secondary":
            entrance_type = "ECaveEntranceType::Secondary"
        case _:
            print(
                f"Unknown entrance type: {entrance.entrance_type}, defaulting to Exit"
            )
            entrance_type = "ECaveEntranceType::Exit"
    new_entrance["Data"][2]["Value"] = entrance_type
    new_entrance["ObjectName"] = f"EntranceFeature_{num}"
    new_entrance["OuterIndex"] = outer_index
    new_entrance["CreateBeforeCreateDependencies"] = [outer_index]
    return new_entrance


def build_hemisphere(hdata: dict):
    return Hemisphere(
        (hdata["Location"]["X"], hdata["Location"]["Y"], hdata["Location"]["Z"]),
        hdata["HRange"],
        hdata["VRange"],
    )


def build_entrance(edata: dict):
    return Entrance(
        (edata["Location"]["X"], edata["Location"]["Y"], edata["Location"]["Z"]),
        edata["Type"],
        (
            edata["Direction"]["Roll"],
            edata["Direction"]["Pitch"],
            edata["Direction"]["Yaw"],
        ),
    )


def parse_room_json(room_json: dict):
    floodfilllines = []
    for ffill in room_json["FloodFillLines"]:
        line = [build_hemisphere(l) for l in room_json["FloodFillLines"][ffill]["Points"]]
        floodfilllines.append(line)
    entrances = [build_entrance(v) for _, v in room_json["Entrances"].items()]
    return floodfilllines, entrances

def generate_random_selector(drs: dict, drsr: dict, selector_refs: list, asset_list: list, outer_index: int) -> tuple[dict, list]:
    new_rs = copy.deepcopy(drs)
    new_references = []
    new_references_idx = []
    for selector in selector_refs:
        try:
            index_ref = asset_list.index(selector) + 1
        except ValueError:
            print(f"RandomSelector reference {selector} not found in list: {asset_list}. Skipping.")
            continue
        new_reference = copy.deepcopy(drsr)
        new_reference["Value"] = index_ref
        new_references_idx.append(index_ref)
        new_references.append(new_reference)
    new_rs["Data"][2]["Value"] = new_references
    new_rs["CreateBeforeSerializationDependencies"] = new_references_idx
    new_rs["CreateBeforeCreateDependencies"] = [outer_index]
    new_rs["OuterIndex"] = outer_index
    return new_rs, new_references_idx
                
           

def generate_room(dr, drr, tags, bounds, outer_index, name, selector_idx_list):
    new_room = copy.deepcopy(dr)
    new_room["Data"][1]["Value"] = float(bounds)
    new_room["Data"][2]["Value"][0]["Value"] = tags
    new_room["ObjectName"] = name
    references = []
    for ii in range(outer_index - 1):
        if ii + 1 not in selector_idx_list:
            new_reference = copy.deepcopy(drr)
            new_reference["Name"] = str(ii)
            new_reference["Value"] = ii + 1
            references.append(new_reference)
    new_room["Data"][0]["Value"] = references
    print(selector_idx_list)
    new_room["CreateBeforeSerializationDependencies"] = [
        x for x in range(1, outer_index) if x not in selector_idx_list
    ] + [-13]
    return new_room


def build_json_and_uasset(room_json: dict):

    FLOODFILLLINES, ENTRANCES = parse_room_json(room_json)
    ROOM_NAME = room_json["Name"]
    TAGS = room_json["Tags"]
    BOUNDS = room_json["Bounds"]
    PATH = f"/Game/Maps/Rooms/RoomGenerators/{ROOM_NAME}"
    if room_json.get("RandomSelectors") is None:
        random_sel_num = 0
    else:
        random_sel_num = len(room_json["RandomSelectors"])
    OUTER_ROOM_INDEX = len(room_json["FloodFillLines"]) + len(room_json["Entrances"]) + random_sel_num + 1

    asset_list = [k for k in room_json["FloodFillLines"]] + [k for k in room_json["Entrances"]]

    with open("assets/default_assets/default_floodfillline.json", "r") as f:
        default_floodfillline = json.load(f)
    with open("assets/default_assets/default_roomlinepoint.json", "r") as f:
        default_roomlinepoint = json.load(f)
    with open("assets/default_assets/default_entrance.json", "r") as f:
        default_entrance = json.load(f)
    with open("assets/default_assets/default_room.json", "r") as f:
        default_room = json.load(f)
    with open("assets/default_assets/default_room_reference.json", "r") as f:
        default_room_reference = json.load(f)
    with open("assets/default_assets/default_asset.json", "r") as f:
        default_asset = json.load(f)
    with open("assets/default_assets/default_randomselector.json", "r") as f:
        default_random_selector = json.load(f)
    with open("assets/default_assets/default_randomselector_reference.json", "r") as f:
        default_random_selector_reference = json.load(f)

    floodfill_list = [
        generate_floodfill(
            default_floodfillline,
            default_roomlinepoint,
            ffill,
            ii,
            OUTER_ROOM_INDEX
        )
        for ii, ffill in enumerate(FLOODFILLLINES)
    ]
    entrance_list = [
        generate_entrance(default_entrance, e, ii, OUTER_ROOM_INDEX)
        for ii, e in enumerate(ENTRANCES)
    ]

    selector_list = []
    selector_idx_list = []
    if room_json.get("RandomSelectors"):
        for selector in room_json["RandomSelectors"]:
            new_sel_json, sel_idx = generate_random_selector(default_random_selector, default_random_selector_reference, room_json["RandomSelectors"][selector], asset_list, OUTER_ROOM_INDEX)
            selector_list.append(new_sel_json)
            selector_idx_list.extend(sel_idx)

    room = generate_room(
        default_room,
        default_room_reference,
        TAGS,
        BOUNDS,
        OUTER_ROOM_INDEX,
        ROOM_NAME,
        selector_idx_list
    )

    for ffill in floodfill_list:
        default_asset["Exports"].append(ffill)
    for entrance in entrance_list:
        default_asset["Exports"].append(entrance)
    for selector in selector_list:
        print(selector)
        default_asset["Exports"].append(selector)
    default_asset["Exports"].append(room)
    for tag in TAGS:
        if tag not in default_asset["NameMap"]:
            default_asset["NameMap"].append(tag)
    default_asset["NameMap"][0] = PATH
    default_asset["NameMap"][50] = ROOM_NAME

    with open(f"assets/{ROOM_NAME}.json", "w") as f:
        json.dump(default_asset, f, indent=4)

    # We generate the asset:
    JSON_to_uasset(f"assets/{ROOM_NAME}.json", ROOM_NAME)
