from collections import namedtuple
import copy
import json

from uassetgen import JSON_to_uasset

Hemisphere = namedtuple("Hemisphere", ["center", "radius", "height"])
Entrance = namedtuple("Entrance", ["location", "entrance_type", "orientation"])


def generate_floodfill(df, dr, fflines, num, ffill_num, entrance_num):
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
    outer_index = ffill_num + entrance_num + 1
    new_ffill["OuterIndex"] = outer_index
    new_ffill["CreateBeforeCreateDependencies"] = [outer_index]
    return new_ffill


def generate_entrance(de, entrance, num, ffill_num, entrance_num):
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
    outer_index = ffill_num + entrance_num + 1
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
        line = [build_hemisphere(l) for l in room_json["FloodFillLines"][ffill]]
        floodfilllines.append(line)
    entrances = [build_entrance(v) for _, v in room_json["Entrances"].items()]
    return floodfilllines, entrances


def generate_room(dr, drr, tags, bounds, num_fflines, num_entrances, name):
    new_room = copy.deepcopy(dr)
    new_room["Data"][1]["Value"] = float(bounds)
    new_room["Data"][2]["Value"][0]["Value"] = tags
    new_room["ObjectName"] = name
    references = []
    for ii in range(num_fflines + num_entrances):
        new_reference = copy.deepcopy(drr)
        new_reference["Name"] = str(ii)
        new_reference["Value"] = ii + 1
        references.append(new_reference)
    new_room["Data"][0]["Value"] = references
    outer_index = num_fflines + num_entrances + 1
    new_room["CreateBeforeSerializationDependencies"] = [
        x for x in range(1, outer_index)
    ] + [-13]
    return new_room


def build_json_and_uasset(room_json: dict):

    FLOODFILLLINES, ENTRANCES = parse_room_json(room_json)
    ROOM_NAME = room_json["Name"]
    TAGS = room_json["Tags"]
    BOUNDS = room_json["Bounds"]
    PATH = f"/Game/Maps/Rooms/RoomGenerators/{ROOM_NAME}"

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

    floodfill_list = [
        generate_floodfill(
            default_floodfillline,
            default_roomlinepoint,
            ffill,
            ii,
            len(FLOODFILLLINES),
            len(ENTRANCES),
        )
        for ii, ffill in enumerate(FLOODFILLLINES)
    ]
    entrance_list = [
        generate_entrance(default_entrance, e, ii, len(FLOODFILLLINES), len(ENTRANCES))
        for ii, e in enumerate(ENTRANCES)
    ]
    room = generate_room(
        default_room,
        default_room_reference,
        TAGS,
        BOUNDS,
        len(FLOODFILLLINES),
        len(ENTRANCES),
        ROOM_NAME,
    )

    for ffill in floodfill_list:
        default_asset["Exports"].append(ffill)
    for entrance in entrance_list:
        default_asset["Exports"].append(entrance)
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
