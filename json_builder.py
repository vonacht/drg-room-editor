from dataclasses import dataclass, field
import copy
import json

from uassetgen import JSON_to_uasset

@dataclass 
class PillarRange:
    min: float 
    max: float 

    @classmethod 
    def from_dict(cls, data: dict): 
        json_to_dataclass_map = {
                "Max": "max",
                "Min": "min"
        }
        adjusted_dict = {json_to_dataclass_map[k]:v for k, v in data.items()}
        return cls(**adjusted_dict)

@dataclass 
class Location:
    x: float 
    y: float 
    z: float

    @classmethod 
    def from_dict(cls, data: dict): 
        json_to_dataclass_map = {
                "X": "x",
                "Y": "y",
                "Z": "z"
        }
        adjusted_dict = {json_to_dataclass_map[k]:v for k, v in data.items()}
        return cls(**adjusted_dict)

@dataclass 
class PillarPoint:
    location: Location
    points_range: PillarRange = field(default_factory=lambda: PillarRange(min=100, max=100))
    noise_range: PillarRange = field(default_factory=lambda: PillarRange(min=150, max=150))
    skew_factor: PillarRange = field(default_factory=lambda: PillarRange(min=0, max=0))
    fill_amount: PillarRange = field(default_factory=lambda: PillarRange(min=100, max=100))

    @classmethod 
    def from_dict(cls, data: dict): 
        json_to_dataclass_map = {
                "Location": "location",
                "Range": "points_range",
                "FillAmount": "fill_amount",
                "SkewFactor": "skew_factor",
                "NoiseRange": "noise_range"
        }
        builder_map = {
                "Location": Location.from_dict,
                "Range": PillarRange.from_dict,
                "FillAmount": PillarRange.from_dict,
                "SkewFactor": PillarRange.from_dict,
                "NoiseRange": PillarRange.from_dict
        }
        adjusted_dict = {json_to_dataclass_map[k]:builder_map[k](v) for k, v in data.items()}
        return cls(**adjusted_dict)

@dataclass 
class FloodFillPillar:
    points: list[PillarPoint]
    range_scale: PillarRange = field(default_factory=lambda: PillarRange(min=1, max=1))
    noise_range_scale: PillarRange = field(default_factory=lambda: PillarRange(min=1, max=1))

    @classmethod 
    def from_dict(cls, data: dict): 
        json_to_dataclass_map = {
                "Points": "points",
                "RangeScale": "range_scale",
                "NoiseRangeScale": "noise_range_scale"
        }
        builder_map = {
                "Points": PillarPoint.from_dict,
                "RangeScale": PillarRange.from_dict,
                "NoiseRangeScale": PillarRange.from_dict
                }

        adjusted_dict = {}
        for k, v in data.items():
            if k == "Points":
                adjusted_dict["points"] = [builder_map["Points"](point) for point in v]
            else:
                adjusted_dict[json_to_dataclass_map[k]] = builder_map[k](v)
        return cls(**adjusted_dict)


@dataclass
class FloodFillLine:
    location: tuple
    hrange: float 
    vrange: float 
    ceiling_height: float = 900 
    floor_depth: float = 0 
    floor_angle: float = 0
    ceiling_noise_range: float = 100
    wall_noise_range: float = 100
    floor_noise_range: float = 100
    height_scale: float = 1

    @classmethod
    def from_dict(cls, data: dict):
        json_to_dataclass_map = {
            "Location": "location",
            "HRange": "hrange",
            "VRange": "vrange",
            "CeilingHeight": "ceiling_height",
            "FloorDepth": "floor_depth",
            "FloorAngle": "floor_angle",
            "CeilingNoiseRange": "ceiling_noise_range",
            "WallNoiseRange": "wall_noise_range",
            "FloorNoiseRange": "floor_noise_range"
        }
        adjusted_dict = {json_to_dataclass_map[k]:v for k, v in data.items()}
        adjusted_dict["location"] = (data["Location"]["X"], data["Location"]["Y"], data["Location"]["Z"])
        return cls(**adjusted_dict)

@dataclass 
class Entrance:
    location: tuple 
    entrance_type: str
    rotator: tuple

    @classmethod 
    def from_dict(cls, data: dict):
        json_to_dataclass_map = {
            "Location": "location",
            "Type": "entrance_type",
            "Direction": "rotator"
        }
        adjusted_dict = {json_to_dataclass_map[k]:v for k, v in data.items()}
        adjusted_dict["location"] = (data["Location"]["X"], data["Location"]["Y"], data["Location"]["Z"])
        adjusted_dict["rotator"] = (data["Direction"]["Roll"], data["Direction"]["Pitch"], data["Direction"]["Yaw"])
        return cls(**adjusted_dict)


def generate_floodfill(df, dr, fflines, num, outer_index):
    points = []
    new_ffill = copy.deepcopy(df)
    for point in fflines:
        new_point = copy.deepcopy(dr)
        new_point["Value"][0]["Value"][0]["Value"]["X"] = point.location[0]
        new_point["Value"][0]["Value"][0]["Value"]["Y"] = point.location[1]
        new_point["Value"][0]["Value"][0]["Value"]["Z"] = point.location[2]
        new_point["Value"][1]["Value"] = point.hrange
        new_point["Value"][2]["Value"] = point.vrange
        new_point["Value"][3]["Value"] = point.ceiling_noise_range
        new_point["Value"][4]["Value"] = point.wall_noise_range
        new_point["Value"][5]["Value"] = point.floor_noise_range
        new_point["Value"][6]["Value"] = point.ceiling_height
        new_point["Value"][7]["Value"] = point.height_scale
        new_point["Value"][8]["Value"] = point.floor_depth
        new_point["Value"][9]["Value"] = point.floor_angle
        points.append(new_point)
    new_ffill["Data"][0]["Value"] = points
    new_ffill["ObjectName"] = f"FloodFillLine_{num}"
    new_ffill["OuterIndex"] = outer_index
    new_ffill["CreateBeforeCreateDependencies"] = [outer_index]
    return new_ffill


def generate_entrance(de, entrance, num, outer_index):
    new_entrance = copy.deepcopy(de)
    new_entrance["Data"][0]["Value"][0]["Value"]["X"] = entrance.location[0]
    new_entrance["Data"][0]["Value"][0]["Value"]["Y"] = entrance.location[1]
    new_entrance["Data"][0]["Value"][0]["Value"]["Z"] = entrance.location[2]
    new_entrance["Data"][1]["Value"][0]["Value"]["Pitch"] = entrance.rotator[1]
    new_entrance["Data"][1]["Value"][0]["Value"]["Yaw"] = entrance.rotator[2]
    new_entrance["Data"][1]["Value"][0]["Value"]["Roll"] = entrance.rotator[0]
    match entrance.entrance_type:
        case "Exit":
            entrance_type = "ECaveEntranceType::Exit"
        case "Entrance":
            entrance_type = "ECaveEntranceType::Entrance"
        case "Secondary":
            entrance_type = "ECaveEntrancePriority::Secondary"
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

def generate_pillar_point(dpp: dict, pillar_point: PillarPoint) -> dict:
    new_pillar_point = copy.deepcopy(dpp)
    new_pillar_point["Value"][0]["Value"][0]["Value"]["X"] = pillar_point.location.x
    new_pillar_point["Value"][0]["Value"][0]["Value"]["Y"] = pillar_point.location.y
    new_pillar_point["Value"][0]["Value"][0]["Value"]["Z"] = pillar_point.location.z
    new_pillar_point["Value"][1]["Value"][0]["Value"] = pillar_point.points_range.min
    new_pillar_point["Value"][1]["Value"][1]["Value"] = pillar_point.points_range.max
    new_pillar_point["Value"][2]["Value"][0]["Value"] = pillar_point.noise_range.min
    new_pillar_point["Value"][2]["Value"][1]["Value"] = pillar_point.noise_range.max
    new_pillar_point["Value"][3]["Value"][0]["Value"] = pillar_point.skew_factor.min
    new_pillar_point["Value"][3]["Value"][1]["Value"] = pillar_point.skew_factor.max
    new_pillar_point["Value"][4]["Value"][0]["Value"] = pillar_point.fill_amount.min
    new_pillar_point["Value"][4]["Value"][1]["Value"] = pillar_point.fill_amount.max

    return new_pillar_point

def generate_floodfillpillar(dp, dpp, pillar, num, outer_index):
    new_pillar = copy.deepcopy(dp)
    new_pillar["Data"][0]["Value"] = [generate_pillar_point(dpp, p) for p in pillar.points]
    # RangeScale:
    new_pillar["Data"][1]["Value"][0]["Value"] = pillar.range_scale.min
    new_pillar["Data"][1]["Value"][1]["Value"] = pillar.range_scale.max
    # NoiseRangeScale:
    new_pillar["Data"][2]["Value"][0]["Value"] = pillar.noise_range_scale.min
    new_pillar["Data"][2]["Value"][1]["Value"] = pillar.noise_range_scale.max
    new_pillar["ObjectName"] = f"FloodFillPillar_{num}"
    new_pillar["OuterIndex"] = outer_index
    new_pillar["CreateBeforeCreateDependencies"] = [outer_index]
    return new_pillar

def parse_room_json(room_json: dict) -> tuple:
    floodfilllines = []
    for ffill in room_json["FloodFillLines"]:
        line = [FloodFillLine.from_dict(l) for l in room_json["FloodFillLines"][ffill]["Points"]]
        floodfilllines.append(line)
    entrances = [Entrance.from_dict(v) for _, v in room_json["Entrances"].items()]
    pillars = [FloodFillPillar.from_dict(v) for _, v in room_json["FloodFillPillars"].items()]
    return floodfilllines, entrances, pillars


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

    FLOODFILLLINES, ENTRANCES, PILLARS = parse_room_json(room_json)
    ROOM_NAME = room_json["Name"]
    TAGS = room_json["Tags"]
    BOUNDS = room_json["Bounds"]
    PATH = f"/Game/Maps/Rooms/RoomGenerators/{ROOM_NAME}"
    if room_json.get("RandomSelectors") is None:
        random_sel_num = 0
    else:
        random_sel_num = len(room_json["RandomSelectors"])
    if room_json.get("FloodFillPillars") is None:
        pillars_num  = 0
    else:
        pillars_num  = len(room_json["FloodFillPillars"])
    OUTER_ROOM_INDEX = len(room_json["FloodFillLines"]) + len(room_json["Entrances"]) + random_sel_num + pillars_num + 1

    asset_list = [k for k in room_json["FloodFillLines"]] + [k for k in room_json["Entrances"]] + [k for k in room_json["FloodFillPillars"]]

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
    with open("assets/default_assets/default_pillar_point.json", "r") as f:
        default_pillar_point = json.load(f)
    with open("assets/default_assets/default_pillar.json", "r") as f:
        default_pillar = json.load(f)

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
    pillar_list = [
        generate_floodfillpillar(default_pillar, default_pillar_point, p, ii, OUTER_ROOM_INDEX)
        for ii, p in enumerate(PILLARS)
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
    for pillar in pillar_list:
        default_asset["Exports"].append(pillar)
    for selector in selector_list:
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
