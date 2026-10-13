# ship.py — системы корабля, слоты деталей, инвентарь, износ, эффекты,
#            типы кораблей, сериализация.

import random
from data import (FUEL_MAX, FUEL_BURN_PER_SEC,
                  O2_MAX, O2_BURN_PER_SEC,
                  O2_RESERVE_MAX, O2_RESERVE_BURN_PER_SEC,
                  SYSTEM_SLOTS, PARTS_BY_ID,
                  SYSTEM_CRITICAL, SYSTEM_WARNING,
                  INVENTORY_MAX_WEIGHT,
                  ACCIDENT_DAMAGE_MIN, ACCIDENT_DAMAGE_MAX,
                  ACCIDENT_COOLDOWN_MIN, ACCIDENT_COOLDOWN_MAX,
                  START_MONEY, START_FUEL, START_O2, clamp)
from ships_data import SHIPS_BY_ID, STARTING_SHIP_ID
from data import SCRAP_BY_ID, VALUABLES_BY_ID

class PartInstance:
    """Экземпляр детали. Хранит id, текущий HP и макс HP."""

    def __init__(self, part_id, hp=None):
        info = PARTS_BY_ID[part_id]
        self.part_id = part_id
        self.hp_max = info["hp_max"]
        self.hp = self.hp_max if hp is None else clamp(hp, 0.0, self.hp_max)

    @property
    def info(self):
        return PARTS_BY_ID[self.part_id]

    @property
    def name(self):
        return self.info["name"]

    @property
    def weight(self):
        return self.info["weight"]

    @property
    def wear_rate(self):
        return self.info["wear_rate"]

    @property
    def effects(self):
        return self.info.get("effects", {})

    @property
    def tier_for(self):
        return self.info.get("tier_for", self.part_id)

    @property
    def hp_pct(self):
        return clamp(self.hp / self.hp_max, 0.0, 1.0)

    def wear(self, dt):
        self.hp = clamp(self.hp - self.wear_rate * dt, 0.0, self.hp_max)

    def is_broken(self):
        return self.hp <= 0.01

    def to_dict(self):
        return {"part_id": self.part_id, "hp": self.hp}

    @staticmethod
    def from_dict(d):
        return PartInstance(d["part_id"], hp=d["hp"])


class SystemSlot:
    """Слот системы: содержит либо деталь, либо ничего."""

    def __init__(self, required_part_id):
        self.required_part_id = required_part_id
        self.part = None

    @property
    def is_filled(self):
        return self.part is not None and not self.part.is_broken()


class ShipSystem:
    """Система корабля: список слотов."""

    def __init__(self, sid):
        self.id = sid
        self.slots = [SystemSlot(pid) for pid in SYSTEM_SLOTS[sid]]
        self.hp_bonus = 0.0
        for slot in self.slots:
            slot.part = PartInstance(slot.required_part_id)

    @property
    def hp_pct(self):
        max_h = self.hp_max
        if max_h <= 0:
            return 0.0
        return clamp(self.hp / max_h, 0.0, 1.0)

    @property
    def hp(self):
        if not self.slots:
            return 0.0
        base = min(slot.part.hp if slot.part else 0.0 for slot in self.slots)
        return base + self.hp_bonus

    @property
    def hp_max(self):
        return 100.0 + self.hp_bonus

    @property
    def state(self):
        pct = self.hp_pct
        if pct <= 0.01:
            return "dead"
        if pct * 100 < SYSTEM_CRITICAL:
            return "crit"
        if pct * 100 < SYSTEM_WARNING:
            return "warn"
        return "ok"

    @property
    def is_functional(self):
        for slot in self.slots:
            if slot.part is None or slot.part.is_broken():
                return False
        return True

    def wear(self, dt):
        for slot in self.slots:
            if slot.part is not None:
                slot.part.wear(dt)

    def take_damage(self, amount):
        candidates = [slot for slot in self.slots if slot.part is not None]
        if not candidates:
            return None
        slot = random.choice(candidates)
        slot.part.hp = clamp(slot.part.hp - amount, 0.0, slot.part.hp_max)
        return slot.part.name

    def to_dict(self):
        return {
            "id": self.id,
            "hp_bonus": self.hp_bonus,
            "slots": [
                (slot.part.to_dict() if slot.part is not None else None)
                for slot in self.slots
            ],
        }

    @staticmethod
    def from_dict(d, system_slots_template):
        sys = ShipSystem.__new__(ShipSystem)
        sys.id = d["id"]
        sys.hp_bonus = d.get("hp_bonus", 0.0)
        sys.slots = []
        for i, req_pid in enumerate(system_slots_template):
            slot = SystemSlot(req_pid)
            part_data = d["slots"][i] if i < len(d["slots"]) else None
            if part_data is not None:
                slot.part = PartInstance.from_dict(part_data)
            sys.slots.append(slot)
        return sys


class ShipSystems:
    """Все системы корабля + ресурсы + инвентарь + контракты + эффекты."""

    def __init__(self):
        self.money = float(START_MONEY)
        self.fuel = float(START_FUEL)
        self.o2 = float(START_O2)
        self.o2_reserve = O2_RESERVE_MAX
        
        # Хлам и трофеи (лут с пиратов)
        self.scrap = {}        # {scrap_id: количество}
        self.valuables = {}    # {valuable_id: количество}

        # Тип корабля
        self.ship_type = STARTING_SHIP_ID
        self.cargo_max = SHIPS_BY_ID[self.ship_type]["cargo_max"]

        self.systems = {
            sid: ShipSystem(sid)
            for sid in ("engine", "reactor", "o2gen", "hull", "weapon", "shield")
        }
        
                # У игрока с начала есть базовый лазер в системе "weapon"
        weapon_sys = self.systems["weapon"]
        # Заменяем первую пустую деталь на лазер
        if weapon_sys.slots:
            weapon_sys.slots[0].part = PartInstance("laser_w")

        # Щит изначально пустой (нет генератора)
        shield_sys = self.systems["shield"]
        if shield_sys.slots:
            shield_sys.slots[0].part = None

        # Текущий заряд щита (0, пока нет генератора)
        self.current_shield = 0.0
        
                # Розыск (патрули атакуют)
        self.is_wanted = False

        self.inventory = []

        self.cargo = []
        self.active_contracts = []
        self.total_earned = 0
        self.contracts_completed = 0

        # Сюжет
        from story import StoryManager
        self.story_manager = StoryManager()
        self.quest_cargo = {}

        self.accident_timer = 0.0
        self.accident_cooldown = random.uniform(
            ACCIDENT_COOLDOWN_MIN, ACCIDENT_COOLDOWN_MAX)
        self.last_accident = None

        # Эффекты от деталей
        self.effects = {}
        self.recompute_effects()

    # ---------- Ресурсы ----------

    def consume_fuel(self, amount):
        self.fuel = clamp(self.fuel - amount, 0.0, FUEL_MAX)

    def refuel(self, amount=None):
        if amount is None:
            self.fuel = FUEL_MAX
        else:
            self.fuel = clamp(self.fuel + amount, 0.0, FUEL_MAX)

    def refill_o2_reserve(self):
        self.o2_reserve = O2_RESERVE_MAX

    # ---------- Инвентарь ----------

    def inventory_weight_total(self):
        return sum(p.weight for p in self.inventory)

    def can_add_part(self, part_id):
        info = PARTS_BY_ID[part_id]
        return self.total_weight() + info["weight"] <= self.cargo_max

    def add_new_part(self, part_id):
        if not self.can_add_part(part_id):
            return False
        self.inventory.append(PartInstance(part_id))
        return True

    def add_part_instance(self, part):
        if self.total_weight() + part.weight > self.cargo_max:
            return False
        self.inventory.append(part)
        return True

    def find_part_in_inventory(self, part_id, by_tier=False):
        for i, p in enumerate(self.inventory):
            if by_tier:
                tier = p.info.get("tier_for", p.part_id)
                if tier == part_id:
                    return i
            else:
                if p.part_id == part_id:
                    return i
        return None

    def remove_inventory_at(self, index):
        if 0 <= index < len(self.inventory):
            return self.inventory.pop(index)
        return None

    # ---------- Продажа ----------

    def part_sell_price(self, part):
        base = part.info["price"]
        pct = part.hp / part.hp_max if part.hp_max > 0 else 0.0
        pct = max(0.05, pct)
        return max(1, int(base * pct))

    def sell_part_at(self, index):
        if index < 0 or index >= len(self.inventory):
            return 0
        part = self.inventory[index]
        price = self.part_sell_price(part)
        self.inventory.pop(index)
        self.money += price
        self.total_earned += price
        return price

    # ---------- Хлам и трофеи ----------

    def add_scrap(self, scrap_id, count=1):
        if scrap_id not in SCRAP_BY_ID:
            return False
        self.scrap[scrap_id] = self.scrap.get(scrap_id, 0) + count
        return True

    def add_valuable(self, val_id, count=1):
        if val_id not in VALUABLES_BY_ID:
            return False
        self.valuables[val_id] = self.valuables.get(val_id, 0) + count
        return True

    def scrap_weight(self):
        total = 0.0
        for sid, cnt in self.scrap.items():
            info = SCRAP_BY_ID.get(sid)
            if info is None:
                continue
            total += info["weight"] * cnt
        return total

    def valuables_weight(self):
        total = 0.0
        for vid, cnt in self.valuables.items():
            info = VALUABLES_BY_ID.get(vid)
            if info is None:
                continue
            total += info["weight"] * cnt
        return total

    def scrap_value(self):
        total = 0
        for sid, cnt in self.scrap.items():
            info = SCRAP_BY_ID.get(sid)
            if info is None:
                continue
            total += info["price"] * cnt
        return total

    def valuables_value(self):
        total = 0
        for vid, cnt in self.valuables.items():
            info = VALUABLES_BY_ID.get(vid)
            if info is None:
                continue
            total += info["price"] * cnt
        return total

    def sell_all_scrap(self):
        """Продаёт весь хлам. Возвращает сумму."""
        total = self.scrap_value()
        if total > 0:
            self.scrap = {}
            self.money += total
            self.total_earned += total
        return total

    def sell_all_valuables(self):
        """Продаёт все трофеи. Возвращает сумму."""
        total = self.valuables_value()
        if total > 0:
            self.valuables = {}
            self.money += total
            self.total_earned += total
        return total

    # ---------- Действия со слотами ----------

    def remove_part_from_system(self, sid, slot_index):
        sys = self.systems[sid]
        if slot_index < 0 or slot_index >= len(sys.slots):
            return False
        slot = sys.slots[slot_index]
        if slot.part is None:
            return False
        if not self.add_part_instance(slot.part):
            return False
        slot.part = None
        self.recompute_effects()
        return True

    def install_part_into_system(self, sid, slot_index):
        sys = self.systems[sid]
        if slot_index < 0 or slot_index >= len(sys.slots):
            return False
        slot = sys.slots[slot_index]
        idx = self.find_part_in_inventory(slot.required_part_id, by_tier=True)
        if idx is None:
            return False

        old = slot.part
        if old is not None:
            if not self.add_part_instance(old):
                return False
            slot.part = None

        new_part = self.inventory.pop(idx)
        slot.part = new_part
        self.recompute_effects()
        return True

    # ---------- Груз и контракты ----------

    def cargo_weight(self):
        return sum(c.cargo_weight for c in self.active_contracts)

    def quest_cargo_weight(self):
        total = 0.0
        for qid, data in self.quest_cargo.items():
            if not data.get("collected", False):
                total += data["weight"]
        return total

    def total_weight(self):
        return (self.inventory_weight_total()
                + self.cargo_weight()
                + self.quest_cargo_weight()
                + self.scrap_weight()
                + self.valuables_weight())

    def can_add_cargo(self, weight):
        return self.total_weight() + weight <= self.cargo_max

    def has_contract_to(self, station):
        for c in self.active_contracts:
            if c.to_station is station:
                return True
        return False

    def contracts_to_station(self, station):
        return [c for c in self.active_contracts if c.to_station is station]

    def complete_contracts_to_station(self, station, now):
        to_complete = self.contracts_to_station(station)
        if not to_complete:
            return 0
        total = 0
        for c in to_complete:
            total += c.current_reward(now)
            self.active_contracts.remove(c)
        self.money += total
        self.total_earned += total
        self.contracts_completed += len(to_complete)
        return total

    # ---------- Эффекты ----------

    def recompute_effects(self):
        raw = {}

        for sys_id, sys in self.systems.items():
            hp_bonus = 0.0
            for slot in sys.slots:
                if slot.part is None:
                    continue
                effects = slot.part.info.get("effects", {})
                for k, v in effects.items():
                    if k.startswith("hp_bonus_"):
                        target_sid = k[len("hp_bonus_"):]
                        if target_sid == sys_id:
                            hp_bonus += v
                    else:
                        raw[k] = raw.get(k, 0.0) + v
            sys.hp_bonus = hp_bonus

        self.effects = {}
        self.effects["speed_mult"] = max(0.3, 1.0 + raw.get("speed_bonus", 0.0))
        self.effects["accel_mult"] = max(0.3, 1.0 + raw.get("accel_bonus", 0.0))
        self.effects["fuel_mult"] = max(0.1, 1.0 - raw.get("fuel_save", 0.0))
        self.effects["o2_mult"] = max(0.1, 1.0 - raw.get("o2_save", 0.0))
        for sid in ("engine", "reactor", "o2gen"):
            key = f"wear_reduction_{sid}"
            self.effects[f"wear_{sid}_mult"] = max(
                0.1, 1.0 - raw.get(key, 0.0))

    def get_effect(self, key, default=1.0):
        return self.effects.get(key, default)

    # ---------- Смена корабля ----------

    def apply_ship_type(self, ship_id):
        if ship_id not in SHIPS_BY_ID:
            return False
        self.ship_type = ship_id
        self.cargo_max = SHIPS_BY_ID[ship_id]["cargo_max"]
        self.recompute_effects()
        return True

    def buy_ship(self, ship_id):
        if ship_id not in SHIPS_BY_ID:
            return False
        ship = SHIPS_BY_ID[ship_id]
        price = ship["price"]
        if self.money < price:
            return False

        old_ship = SHIPS_BY_ID.get(self.ship_type, None)
        refund = 0
        if old_ship is not None:
            refund = int(old_ship["price"] * 0.3)

        if self.total_weight() > ship["cargo_max"]:
            return False

        self.money -= price
        self.money += refund
        self.apply_ship_type(ship_id)
        return True

    def get_ship_speed_mult(self):
        ship = SHIPS_BY_ID.get(self.ship_type, None)
        if ship is None:
            return 1.0
        return ship.get("speed_mult", 1.0)

    def get_ship_accel_mult(self):
        ship = SHIPS_BY_ID.get(self.ship_type, None)
        if ship is None:
            return 1.0
        return ship.get("accel_mult", 1.0)

    def get_ship_fuel_mult(self):
        ship = SHIPS_BY_ID.get(self.ship_type, None)
        if ship is None:
            return 1.0
        return ship.get("fuel_mult", 1.0)

    # ---------- Обновление ----------

    def update(self, dt, thrust_scale):
        # Топливо: детали + корабль
        if thrust_scale > 0.01:
            fuel_mult = (self.effects.get("fuel_mult", 1.0)
                         * self.get_ship_fuel_mult())
            burn = FUEL_BURN_PER_SEC * thrust_scale * dt * fuel_mult
            self.consume_fuel(burn)

        # Износ систем
        if thrust_scale > 0.01:
            self.systems["engine"].wear(
                dt * self.effects.get("wear_engine_mult", 1.0))
        self.systems["reactor"].wear(
            dt * self.effects.get("wear_reactor_mult", 1.0))
        self.systems["o2gen"].wear(
            dt * self.effects.get("wear_o2gen_mult", 1.0))

        # Кислород
        o2_mult = self.effects.get("o2_mult", 1.0)
        if self.systems["o2gen"].is_functional:
            self.o2 = clamp(self.o2 + 3.0 * dt, 0.0, O2_MAX)
        else:
            if self.o2 > 0:
                self.o2 = clamp(self.o2 - O2_BURN_PER_SEC * dt * o2_mult,
                                0.0, O2_MAX)
            else:
                self.o2_reserve = clamp(
                    self.o2_reserve - O2_RESERVE_BURN_PER_SEC * dt * o2_mult,
                    0.0, O2_RESERVE_MAX)
                    
        # Регенерация щита
        s_max = self.shield_max
        if s_max > 0:
            s_regen = self.shield_regen
            self.current_shield = clamp(
                self.current_shield + s_regen * dt, 0.0, s_max)

        # Аварии
        self.accident_timer += dt
        if self.accident_timer >= self.accident_cooldown:
            self.accident_timer = 0.0
            self.accident_cooldown = random.uniform(
                ACCIDENT_COOLDOWN_MIN, ACCIDENT_COOLDOWN_MAX)
            self._random_accident()

    def _random_accident(self):
        all_sys = list(self.systems.values())
        random.shuffle(all_sys)
        for sys in all_sys:
            candidates = [s for s in sys.slots if s.part is not None]
            if not candidates:
                continue
            slot = random.choice(candidates)
            dmg = random.uniform(ACCIDENT_DAMAGE_MIN, ACCIDENT_DAMAGE_MAX)
            slot.part.hp = clamp(slot.part.hp - dmg, 0.0, slot.part.hp_max)
            self.last_accident = f"Авария: {sys.id} / {slot.part.name} -{int(dmg)}"
            return
        self.last_accident = None

    # ---------- Проверки ----------

    @property
    def has_fuel(self):
        return self.fuel > 0.01

    @property
    def has_o2(self):
        return self.o2 > 0.01 or self.o2_reserve > 0.01

    @property
    def engine_alive(self):
        return self.systems["engine"].is_functional

    @property
    def can_thrust(self):
        return self.has_fuel and self.engine_alive

    # ---------- Боевые параметры ----------

    @property
    def weapon_damage(self):
        """Суммарный урон оружия (за выстрел)."""
        w = self.systems.get("weapon", None)
        if w is None:
            return 0.0
        total = 0.0
        for slot in w.slots:
            if slot.part is None or slot.part.is_broken():
                continue
            effects = slot.part.info.get("effects", {})
            total += effects.get("weapon_damage", 0.0)
        return total

    @property
    def weapon_rate(self):
        """Скорость стрельбы (секунд между выстрелами). 0 = нет оружия."""
        w = self.systems.get("weapon", None)
        if w is None:
            return 0.0
        rates = []
        for slot in w.slots:
            if slot.part is None or slot.part.is_broken():
                continue
            effects = slot.part.info.get("effects", {})
            if "weapon_rate" in effects:
                rates.append(effects["weapon_rate"])
        if not rates:
            return 0.0
        # Берём минимальную (быстрее стреляем)
        return min(rates)

    @property
    def weapon_radius(self):
        """Радиус действия оружия."""
        if self.weapon_damage <= 0:
            return 0
        return 800.0

    @property
    def shield_max(self):
        """Максимум щита."""
        s = self.systems.get("shield", None)
        if s is None:
            return 0.0
        total = 0.0
        for slot in s.slots:
            if slot.part is None or slot.part.is_broken():
                continue
            effects = slot.part.info.get("effects", {})
            total += effects.get("shield_max", 0.0)
        return total

    @property
    def shield_regen(self):
        """Регенерация щита в секунду."""
        s = self.systems.get("shield", None)
        if s is None:
            return 0.0
        total = 0.0
        for slot in s.slots:
            if slot.part is None or slot.part.is_broken():
                continue
            effects = slot.part.info.get("effects", {})
            total += effects.get("shield_regen", 0.0)
        return total

    def take_damage_hull(self, amount):
        """Наносит урон игроку: сначала по щиту, потом по корпусу.

        Возвращает True, если корабль уничтожен (корпус = 0).
        """
        # Щит
        if self.current_shield > 0:
            absorbed = min(self.current_shield, amount)
            self.current_shield -= absorbed
            amount -= absorbed

        if amount <= 0:
            return False

        # Корпус: урон бьёт в детали системы hull
        hull = self.systems.get("hull", None)
        if hull is None:
            return False
        # Распределяем урон: сначала по одной случайной детали, потом по другой
        remaining = amount
        candidates = [slot for slot in hull.slots if slot.part is not None]
        if not candidates:
            return True  # нет деталей = корабль уничтожен
        for slot in candidates:
            if remaining <= 0:
                break
            dmg = min(slot.part.hp, remaining)
            slot.part.hp = clamp(slot.part.hp - dmg, 0.0, slot.part.hp_max)
            remaining -= dmg
        return not hull.is_functional

    # ---------- Сериализация ----------

    def to_dict(self):
        from contracts import contract_to_dict
        return {
            "money": self.money,
            "fuel": self.fuel,
            "o2": self.o2,
            "o2_reserve": self.o2_reserve,
            "current_shield": self.current_shield,
            "ship_type": self.ship_type,
            "is_wanted": self.is_wanted,
            "systems": {sid: sys.to_dict() for sid, sys in self.systems.items()},
            "inventory": [p.to_dict() for p in self.inventory],
            "active_contracts": [contract_to_dict(c) for c in self.active_contracts],
            "total_earned": self.total_earned,
            "contracts_completed": self.contracts_completed,
            "accident_timer": self.accident_timer,
            "accident_cooldown": self.accident_cooldown,
            "story": self.story_manager.to_dict(),
            "quest_cargo": self.quest_cargo,
            "scrap": self.scrap,
            "valuables": self.valuables,
        }

    def apply_dict(self, d, station_lookup):
        from data import SYSTEM_SLOTS
        from contracts import contract_from_dict

        self.money = d.get("money", self.money)
        self.fuel = d.get("fuel", self.fuel)
        self.o2 = d.get("o2", self.o2)
        self.o2_reserve = d.get("o2_reserve", self.o2_reserve)
        self.current_shield = d.get("current_shield", 0.0)
        self.is_wanted = d.get("is_wanted", False)

        # Тип корабля
        ship_id = d.get("ship_type", STARTING_SHIP_ID)
        if ship_id in SHIPS_BY_ID:
            self.ship_type = ship_id
            self.cargo_max = SHIPS_BY_ID[ship_id]["cargo_max"]
        else:
            self.ship_type = STARTING_SHIP_ID
            self.cargo_max = SHIPS_BY_ID[STARTING_SHIP_ID]["cargo_max"]

        for sid, sys_data in d.get("systems", {}).items():
            if sid in self.systems:
                template = SYSTEM_SLOTS[sid]
                self.systems[sid] = ShipSystem.from_dict(sys_data, template)

        self.inventory = [
            PartInstance.from_dict(p) for p in d.get("inventory", [])
        ]

        self.active_contracts = []
        for c_data in d.get("active_contracts", []):
            c = contract_from_dict(c_data, station_lookup)
            if c is not None:
                self.active_contracts.append(c)

        self.total_earned = d.get("total_earned", 0)
        self.contracts_completed = d.get("contracts_completed", 0)
        self.accident_timer = d.get("accident_timer", 0.0)
        self.accident_cooldown = d.get("accident_cooldown", 90.0)

        story_data = d.get("story", None)
        if story_data is not None:
            self.story_manager.apply_dict(story_data)
        self.quest_cargo = d.get("quest_cargo", {})

        # Хлам и трофеи
        self.scrap = d.get("scrap", {})
        self.valuables = d.get("valuables", {})

        self.recompute_effects()