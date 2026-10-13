# ships_data.py — характеристики кораблей.
# Чтобы добавить новый корабль — просто допиши словарь в SPACESHIPS.

SPACESHIPS = [
    {
        "id": "drifter",
        "name": "Скиталец",
        "price": 0,
        "cargo_max": 80.0,
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
        "speed_mult": 0.8,
        "accel_mult": 0.8,
        "fuel_mult": 1.2,
        "description": "Тяжёлый грузовик. Большой трюм, но медленный и жрёт топливо.",
    },
    {
        "id": "courier",
        "name": "Курьер",
        "price": 25000,
        "cargo_max": 50.0,
        "speed_mult": 1.4,
        "accel_mult": 1.3,
        "fuel_mult": 0.7,
        "description": "Быстрый и экономичный. Маленький трюм.",
    },
]


SHIPS_BY_ID = {s["id"]: s for s in SPACESHIPS}
STARTING_SHIP_ID = "drifter"