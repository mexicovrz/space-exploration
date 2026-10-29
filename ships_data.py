# ships_data.py — характеристики кораблей.
# Чтобы добавить новый корабль — просто допиши словарь в SPACESHIPS.

SPACESHIPS = [
    {
        "id": "drifter",
        "name": "Скиталец",
        "price": 0,
        "cargo_max": 80.0,
        "fuel_max": 100.0,
        "speed_mult": 1.0,
        "accel_mult": 1.0,
        "fuel_mult": 1.0,
        "description": "Стандартный корабль. Сбалансированные характеристики.",
    },
    {
        "id": "hauler",
        "name": "Тягач",
        "price": 15000,
        "cargo_max": 150.0,
        "fuel_max": 180.0,
        "speed_mult": 0.8,
        "accel_mult": 0.8,
        "fuel_mult": 1.2,
        "module_slots": {
            "engine2": ["pipe_m", "gear_m", "bearing_m"],
        },
        "module_layout": {
            "weapon": ["laser_w"],
        },
        "description": "Второй двигатель нужно установить отдельно. Большой трюм.",
    },
    {
        "id": "courier",
        "name": "Курьер",
        "price": 25000,
        "cargo_max": 50.0,
        "fuel_max": 70.0,
        "speed_mult": 1.4,
        "accel_mult": 1.3,
        "fuel_mult": 0.7,
        "module_slots": {
            "weapon": ["laser_w"],
        },
        "description": "Два лазерных модуля. Быстрый, но с маленьким трюмом.",
    },
    {
        "id": "battleship",
        "name": "Броненосец",
        "price": 75000,
        "cargo_max": 100.0,
        "fuel_max": 140.0,
        "speed_mult": 0.95,
        "accel_mult": 0.9,
        "fuel_mult": 1.4,
        "module_slots": {
            "weapon": ["laser_w", "launcher_w", "laser_w"],
        },
        "description": "Пять слотов вооружения; дополнительные модули нужно купить.",
    },
]


SHIPS_BY_ID = {s["id"]: s for s in SPACESHIPS}
STARTING_SHIP_ID = "drifter"