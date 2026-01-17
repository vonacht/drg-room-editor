from dataclasses import dataclass, field
import copy
import json
import logging

from uassetgen import JSON_to_uasset

SERIALIZATION_DEPENDENCIES = {
    "FloodFillLine": {
        "Normal": [-2, -7],
        "PE": [-8, -14]
        },
    "Entrances": {
        "Normal": [-1, -6],
        "PE": [-7, -13]
        },
    "FloodFillPillar": {
        "Normal": [-3, -8],
        "PE": [-9, -15]
        },
    "RandomSelector": {
        "Normal": [-4, -11],
        "PE": [-10, -19]
        },
    "Room": {
        "Normal": [-5, -12],
        "PE": [-11, -20]
        },
    "PE_MiningHead": {
        "PE": [-6, -12]
        },
    "PE_PodDropDown": {
        "PE": [-6, -12]
       }
}

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


def generate_floodfill(df, dr, fflines, num, outer_index, room_is_pe):
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
    if room_is_pe:
        serialization_idx = SERIALIZATION_DEPENDENCIES["FloodFillLine"]["PE"]
    else:
        serialization_idx = SERIALIZATION_DEPENDENCIES["FloodFillLine"]["Normal"]
    new_ffill["ClassIndex"] = serialization_idx[0]
    new_ffill["TemplateIndex"] = serialization_idx[1]
    new_ffill["SerializationBeforeCreateDependencies"] = serialization_idx
    return new_ffill


def generate_pe_minehead(dm, minehead, num, outer_index):
    new_minehead = copy.deepcopy(dm)
    new_minehead["Data"][0]["Value"][0]["Value"]["X"] = minehead.x
    new_minehead["Data"][0]["Value"][0]["Value"]["Y"] = minehead.y
    new_minehead["Data"][0]["Value"][0]["Value"]["Z"] = minehead.z
    new_minehead["ObjectName"] = f"DropPodCalldownLocationFeature_{num}"
    new_minehead["OuterIndex"] = outer_index
    new_minehead["CreateBeforeCreateDependencies"] = [outer_index]
    serialization_idx = SERIALIZATION_DEPENDENCIES["PE_MiningHead"]["PE"]
    new_minehead["ClassIndex"] = serialization_idx[0]
    new_minehead["TemplateIndex"] = serialization_idx[1]
    new_minehead["SerializationBeforeCreateDependencies"] = serialization_idx
    return new_minehead


def generate_pe_droppoddown(dd, pod, num, outer_index):
    new_minehead = copy.deepcopy(dd)
    new_minehead["Data"][0]["Value"][0]["Value"]["X"] = pod.x
    new_minehead["Data"][0]["Value"][0]["Value"]["Y"] = pod.y
    new_minehead["Data"][0]["Value"][0]["Value"]["Z"] = pod.z
    new_minehead["ObjectName"] = f"DropPodCalldownLocationFeature_{num+1}"
    new_minehead["OuterIndex"] = outer_index
    new_minehead["CreateBeforeCreateDependencies"] = [outer_index]
    serialization_idx = SERIALIZATION_DEPENDENCIES["PE_PodDropDown"]["PE"]
    new_minehead["ClassIndex"] = serialization_idx[0]
    new_minehead["TemplateIndex"] = serialization_idx[1]
    new_minehead["SerializationBeforeCreateDependencies"] = serialization_idx
    return new_minehead


def generate_entrance(de, entrance, num, outer_index, room_is_pe):
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
            logging.warning(
                f"Unknown entrance type: {entrance.entrance_type}, defaulting to Exit"
            )
            entrance_type = "ECaveEntranceType::Exit"
    new_entrance["Data"][2]["Value"] = entrance_type
    new_entrance["ObjectName"] = f"EntranceFeature_{num}"
    new_entrance["OuterIndex"] = outer_index
    new_entrance["CreateBeforeCreateDependencies"] = [outer_index]
    if room_is_pe:
        serialization_idx = SERIALIZATION_DEPENDENCIES["Entrances"]["PE"]
    else:
        serialization_idx = SERIALIZATION_DEPENDENCIES["Entrances"]["Normal"]
    new_entrance["ClassIndex"] = serialization_idx[0]
    new_entrance["TemplateIndex"] = serialization_idx[1]
    new_entrance["SerializationBeforeCreateDependencies"] = serialization_idx
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

def generate_floodfillpillar(dp, dpp, pillar, num, outer_index, room_is_pe):
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
    if room_is_pe:
        serialization_idx = SERIALIZATION_DEPENDENCIES["FloodFillPillar"]["PE"]
    else:
        serialization_idx = SERIALIZATION_DEPENDENCIES["FloodFillPillar"]["Normal"]
    new_pillar["ClassIndex"] = serialization_idx[0]
    new_pillar["TemplateIndex"] = serialization_idx[1]
    new_pillar["SerializationBeforeCreateDependencies"] = serialization_idx
    return new_pillar

def parse_room_json(room_json: dict) -> tuple:
    floodfilllines = []
    for ffill in room_json["FloodFillLines"]:
        line = [FloodFillLine.from_dict(l) for l in room_json["FloodFillLines"][ffill]["Points"]]
        floodfilllines.append(line)
    entrances = [Entrance.from_dict(v) for _, v in room_json["Entrances"].items()]
    if room_json.get("FloodFillPillars"):
        pillars = [FloodFillPillar.from_dict(v) for _, v in room_json["FloodFillPillars"].items()]
    else:
        pillars = None
    if room_json.get("PE_MiningHead"):
        pe_mininghead = [Location.from_dict(v["Location"]) for _, v in room_json["PE_MiningHead"].items()]
    else:
        pe_mininghead = None
    if room_json.get("PE_PodDropDown"):
        pe_poddropdown = [Location.from_dict(v["Location"]) for _, v in room_json["PE_PodDropDown"].items()]
    else:
        pe_poddropdown = None
    return floodfilllines, entrances, pillars, pe_mininghead, pe_poddropdown


def generate_random_selector(drs: dict, drsr: dict, selector_refs: list, asset_list: list, outer_index: int, room_is_pe: bool) -> tuple[dict, list]:
    new_rs = copy.deepcopy(drs)
    new_references = []
    new_references_idx = []
    for selector in selector_refs:
        try:
            index_ref = asset_list.index(selector) + 1
        except ValueError:
            logging.warning(f"RandomSelector reference {selector} not found in list: {asset_list}. Skipping.")
            continue
        new_reference = copy.deepcopy(drsr)
        new_reference["Value"] = index_ref
        new_references_idx.append(index_ref)
        new_references.append(new_reference)
    new_rs["Data"][2]["Value"] = new_references
    new_rs["CreateBeforeSerializationDependencies"] = new_references_idx
    new_rs["CreateBeforeCreateDependencies"] = [outer_index]
    new_rs["OuterIndex"] = outer_index
    if room_is_pe:
        serialization_idx = SERIALIZATION_DEPENDENCIES["RandomSelector"]["PE"]
    else:
        serialization_idx = SERIALIZATION_DEPENDENCIES["RandomSelector"]["Normal"]
    new_rs["ClassIndex"] = serialization_idx[0]
    new_rs["TemplateIndex"] = serialization_idx[1]
    new_rs["SerializationBeforeCreateDependencies"] = serialization_idx
    return new_rs, new_references_idx
                
           

def generate_room(dr, drr, tags, bounds, outer_index, name, selector_idx_list, room_is_pe):
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
    if room_is_pe:
        new_room["CreateBeforeSerializationDependencies"] = [
            x for x in range(1, outer_index) if x not in selector_idx_list
        ] + [-24]
    else:
        new_room["CreateBeforeSerializationDependencies"] = [
            x for x in range(1, outer_index) if x not in selector_idx_list
        ] + [-13] 
    if room_is_pe:
        serialization_idx = SERIALIZATION_DEPENDENCIES["Room"]["PE"]
    else:
        serialization_idx = SERIALIZATION_DEPENDENCIES["Room"]["Normal"]
    new_room["ClassIndex"] = serialization_idx[0]
    new_room["TemplateIndex"] = serialization_idx[1]
    new_room["SerializationBeforeCreateDependencies"] = serialization_idx
    return new_room

def list_nested_keys(main_dict: dict, keys: list) -> list:
    key_views = [list(main_dict.get(key, {}).keys()) for key in keys]
    return [item for sublist in key_views for item in sublist]


def build_json_and_uasset(room_json: dict):

    FLOODFILLLINES, ENTRANCES, PILLARS, PE_MININGHEAD, PE_PODDROPDOWN = parse_room_json(room_json)
    ROOM_NAME = room_json["Name"]
    TAGS = room_json["Tags"]
    BOUNDS = room_json["Bounds"]
    PATH = f"/Game/Maps/Rooms/RoomGenerators/{ROOM_NAME}"

    asset_list = list_nested_keys(room_json, ["FloodFillLines", "Entrances", "FloodFillPillars", "PE_MiningHead", "PE_PodDropDown"])
    room_is_pe = "PE_MiningHead" in room_json or "PE_PodDropDown" in room_json

    OUTER_ROOM_INDEX = len(asset_list) + 1

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
    if room_is_pe:
        with open("assets/default_assets/default_asset_pe.json", "r") as f:
            default_asset = json.load(f)
    else:
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
    with open("assets/default_assets/default_pe_minehead.json", "r") as f:
        default_pe_minehead = json.load(f)
    with open("assets/default_assets/default_pe_droppoddown.json", "r") as f:
        default_pe_droppoddown = json.load(f)


    floodfill_list = [
        generate_floodfill(
            default_floodfillline,
            default_roomlinepoint,
            ffill,
            ii,
            OUTER_ROOM_INDEX,
            room_is_pe
        )
        for ii, ffill in enumerate(FLOODFILLLINES)
    ]
    entrance_list = [
        generate_entrance(default_entrance, e, ii, OUTER_ROOM_INDEX, room_is_pe)
        for ii, e in enumerate(ENTRANCES)
    ]
    
    if "FloodFillPillars" in room_json:
        pillar_list = [
            generate_floodfillpillar(default_pillar, default_pillar_point, p, ii, OUTER_ROOM_INDEX, room_is_pe)
            for ii, p in enumerate(PILLARS)
        ]
    else:
        pillar_list = []

    selector_list = []
    selector_idx_list = []
    if "RandomSelectors" in room_json:
        for selector in room_json["RandomSelectors"]:
            new_sel_json, sel_idx = generate_random_selector(default_random_selector, default_random_selector_reference, room_json["RandomSelectors"][selector], asset_list, OUTER_ROOM_INDEX, room_is_pe)
            selector_list.append(new_sel_json)
            selector_idx_list.extend(sel_idx)

    if "PE_MiningHead" in room_json:
        minehead_list = [
                generate_pe_minehead(default_pe_minehead, minehead, num, OUTER_ROOM_INDEX) for num, minehead in enumerate(PE_MININGHEAD)
        ]
    else:
        minehead_list = []

    if "PE_PodDropDown" in room_json:
        droppoddown_list = [
                generate_pe_droppoddown(default_pe_droppoddown, pod, num, OUTER_ROOM_INDEX) for num, pod in enumerate(PE_PODDROPDOWN)
        ]
    else:
        droppoddown_list = []


    room = generate_room(
        default_room,
        default_room_reference,
        TAGS,
        BOUNDS,
        OUTER_ROOM_INDEX,
        ROOM_NAME,
        selector_idx_list,
        room_is_pe
    )

    for ffill in floodfill_list:
        default_asset["Exports"].append(ffill)
    for entrance in entrance_list:
        default_asset["Exports"].append(entrance)
    for pillar in pillar_list:
        default_asset["Exports"].append(pillar)
    for selector in selector_list:
        default_asset["Exports"].append(selector)
    for minehead in minehead_list:
        default_asset["Exports"].append(minehead)
    for droppoddown_feature in droppoddown_list:
        default_asset["Exports"].append(droppoddown_feature)
    default_asset["Exports"].append(room)
    for tag in TAGS:
        if tag not in default_asset["NameMap"]:
            default_asset["NameMap"].append(tag)
    if room_is_pe:
        default_asset["NameMap"][2] = PATH
        default_asset["NameMap"][52] = ROOM_NAME
    else:
        default_asset["NameMap"][0] = PATH
        default_asset["NameMap"][50] = ROOM_NAME

    #with open(f"assets/{ROOM_NAME}.json", "w") as f:
    #    json.dump(default_asset, f, indent=4)

    # We generate the asset:
    JSON_to_uasset(default_asset, ROOM_NAME)
