# contracts.py — контракты на доставку груза.

import random
from data import (CARGO_DEF, CARGO_BY_ID,
                  CONTRACT_GEN_TIME, CONTRACT_URGENT_DEADLINE,
                  CONTRACT_REWARD_MULT_URGENT, CONTRACT_REWARD_MULT_LATE,
                  CONTRACT_MAX_ACTIVE, CONTRACT_DISTANCE_DIVISOR,
                  STATION_CONTRACTS_COUNT)


class Contract:
    """Контракт на доставку груза с одной станции на другую."""

    def __init__(self, cargo_id, from_station, to_station,
                 reward, urgent=False):
        self.cargo_id = cargo_id
        self.from_station = from_station    # объект Station
        self.to_station = to_station        # объект Station
        self.reward = reward                # базовая награда
        self.urgent = urgent                # срочный ли?
        self.taken = False                  # взят ли игроком
        self.deadline_time = None           # абсолютное игровое время (если срочный)
        self.start_time = None              # когда взят (для расчёта срока)

    @property
    def cargo_info(self):
        return CARGO_BY_ID[self.cargo_id]

    @property
    def cargo_name(self):
        return self.cargo_info["name"]

    @property
    def cargo_weight(self):
        return self.cargo_info["weight"]

    def current_reward(self, now):
        """Сколько заплатит контракт на момент now (с учётом опоздания)."""
        if not self.urgent or self.deadline_time is None:
            return int(self.reward)
        if now <= self.deadline_time:
            return int(self.reward)
        return int(self.reward * CONTRACT_REWARD_MULT_LATE)

    def is_late(self, now):
        return (self.urgent and self.deadline_time is not None
                and now > self.deadline_time)

    def time_left(self, now):
        if not self.urgent or self.deadline_time is None:
            return None
        return max(0.0, self.deadline_time - now)


def station_distance(a, b):
    import math
    return math.hypot(a.pos[0] - b.pos[0], a.pos[1] - b.pos[1])


def make_contract(from_station, to_station, rng):
    """Генерирует один контракт между двумя станциями."""
    cargo_row = rng.choice(CARGO_DEF)
    cargo_id = cargo_row[0]
    weight = cargo_row[2]
    price_per_weight = cargo_row[3]

    dist = station_distance(from_station, to_station)
    dist_mult = 1.0 + dist / CONTRACT_DISTANCE_DIVISOR

    urgent = rng.random() < 0.5
    base_reward = price_per_weight * weight * dist_mult
    if urgent:
        base_reward *= CONTRACT_REWARD_MULT_URGENT

    return Contract(
        cargo_id=cargo_id,
        from_station=from_station,
        to_station=to_station,
        reward=int(base_reward),
        urgent=urgent,
    )


def generate_contracts_for_station(station, all_stations, rng, now):
    """Генерирует STATION_CONTRACTS_COUNT контрактов для станции.

    Меняет station.contracts и station.contracts_generated_time.
    """
    others = [s for s in all_stations if s is not station]
    if not others:
        station.contracts = []
        station.contracts_generated_time = now
        return

    contracts = []
    for _ in range(STATION_CONTRACTS_COUNT):
        target = rng.choice(others)
        contracts.append(make_contract(station, target, rng))

    station.contracts = contracts
    station.contracts_generated_time = now


def take_contract(contract, now, active_list):
    """Помечает контракт как взятый. Возвращает True при успехе."""
    if len(active_list) >= CONTRACT_MAX_ACTIVE:
        return False
    if contract.taken:
        return False
    contract.taken = True
    contract.start_time = now
    if contract.urgent:
        contract.deadline_time = now + CONTRACT_URGENT_DEADLINE
    active_list.append(contract)
    return True


def complete_contract(contract, now):
    """Возвращает сумму награды за контракт."""
    return contract.current_reward(now)
    # ---------- Сериализация ----------

# Глобальная карта: id(station) → (sector_idx, station_idx).
_STATION_REF_MAP = {}


def register_station(station, sector_index, station_index):
    _STATION_REF_MAP[id(station)] = (sector_index, station_index)


def _station_ref(station):
    return list(_STATION_REF_MAP.get(id(station), [-1, -1]))


def contract_to_dict(contract):
    return {
        "cargo_id": contract.cargo_id,
        "reward": contract.reward,
        "urgent": contract.urgent,
        "taken": contract.taken,
        "deadline_time": contract.deadline_time,
        "start_time": contract.start_time,
        "from_ref": _station_ref(contract.from_station),
        "to_ref": _station_ref(contract.to_station),
    }


def contract_from_dict(d, station_lookup):
    from_station, to_station = station_lookup(d["from_ref"], d["to_ref"])
    if from_station is None or to_station is None:
        return None
    c = Contract(
        cargo_id=d["cargo_id"],
        from_station=from_station,
        to_station=to_station,
        reward=d["reward"],
        urgent=d["urgent"],
    )
    c.taken = d.get("taken", False)
    c.deadline_time = d.get("deadline_time")
    c.start_time = d.get("start_time")
    return c