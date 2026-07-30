DEFAULTS = {
    "near_origin_threashold": 400,
    "agenda": {
        "is_enabled": True,
        "monday": {
            "start": None,
            "end": None,
            "state": False,
        },
        "tuesday": {
            "start": None,
            "end": None,
            "state": False,
        },
        "wednesday": {
            "start": "10:00",
            "end": "18:00",
            "state": True,
        },
        "thursday": {
            "start": "10:00",
            "end": "18:00",
            "state": True,
        },
        "friday": {
            "start": "10:00",
            "end": "18:00",
            "state": True,
        },
        "saturday": {
            "start": "10:00",
            "end": "18:00",
            "state": True,
        },
        "sunday": {
            "start": "10:00",
            "end": "18:00",
            "state": True,
        },
    },
    "females": {
        "names": ["female1", "female2", "female3"],
        "share": {
            "motion range": 2000,
        },
    },
    "males": {
        "names": ["male1", "male2"],
        "share": {
            "motion range": 1500,
        },
    },
    "mirrors": {
        "names": ["mirror1", "mirror2", "mirror3"],
        "share": {
            "motion range": 700,
        },
    },
    "dynamixel network": {
        "communication port": None,
        "baudrate": 57600,
    },
    "arduino": {
        "communication port": None,
        "baudrate": 57600,
    },
    "female1": {
        "origin": None,
        "dynamixel id": 1,
        "mirror": {
            "origin": None,
            "dynamixel id": 2,
        },
    },
    "female2": {
        "origin": None,
        "dynamixel id": 3,
        "mirror": {
            "origin": None,
            "dynamixel id": 4,
        },
    },
    "female3": {
        "origin": None,
        "dynamixel id": 5,
        "mirror": {
            "origin": None,
            "dynamixel id": 6,
        },
    },
    "male1": {
        "origin": None,
        "dynamixel id": 7,
    },
    "male2": {
        "origin": None,
        "dynamixel id": 8,
    },
    "bar": {
        "origin": None,
        "dynamixel id": 9,
        "motion range": 10000,
    },
}
