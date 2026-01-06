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
                "type": "object",
                "properties": {
                    "Points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                        "z": {"type": "number"},
                                    },
                                    "required": ["x", "y", "z"],
                                },
                                "hrange": {"type": "number"},
                                "vrange": {"type": "number"},
                            },
                            "required": ["Location", "HRange", "VRange"],
                        },
                    },
                    "RoomFeatures": {"type": "array", "item": "string"}
                },
                "required": ["Points"]
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
            },
        },
        "RandomSelectors": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "item": "string"
            }
        }
    },
    "required": ["Name", "Tags", "Bounds", "FloodFillLines", "Entrances"],
}


def validate_room(json_room: dict):
    validate(json_room, schema=schema)
