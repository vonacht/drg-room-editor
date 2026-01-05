from jsonschema import validate

schema = {
    "type": "object",
    "properties": {
        "Name": {"type": "string"},
        "Bounds": {"type": "number"},
        "Tags": {"type": "array", "items": {"type": "string"}},
        "FloodFillLines": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "Location": {
                            "type": "object",
                            "properties": {
                                "X": {"type": "number"},
                                "Y": {"type": "number"},
                                "Z": {"type": "number"},
                            },
                            "required": ["X", "Y", "Z"],
                        },
                        "HRange": {"type": "number"},
                        "VRange": {"type": "number"},
                    },
                    "required": ["Location", "HRange", "VRange"],
                    "additionalProperties": False,
                },
            },
        },
        "Entrances": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "Location": {
                        "type": "object",
                        "properties": {
                            "X": {"type": "number"},
                            "Y": {"type": "number"},
                            "Z": {"type": "number"},
                        },
                        "required": ["X", "Y", "Z"],
                    },
                    "Type": {
                        "type": "string",
                        "enum": ["Entrance", "Secondary", "Exit"],
                    },
                    "Direction": {
                        "type": "object",
                        "properties": {
                            "Roll": {"type": "number"},
                            "Yaw": {"type": "number"},
                            "Pitch": {"type": "number"},
                        },
                        "required": ["Pitch", "Roll", "Yaw"],
                    },
                },
                "required": ["Location", "Type", "Direction"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["Name", "Tags", "Bounds", "FloodFillLines", "Entrances"],
}


def validate_room(json_room: dict):
    validate(json_room, schema=schema)
