"""Player-built station model: construction, resources, and power allocation.

Energy values are units per in-game hour; simulation input uses in-game
seconds to match ``GameState.game_time``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
import uuid

from station_script import run_station_script, StationScriptError


HUB_COST = {"scrap_metal": 300, "scrap_plate": 100, "electronics": 20}
# Temporary fast-build duration for testing. Construction progress is stored
# in game-hours, while the requested test duration is one game-second.
BUILD_HOURS = 1.0 / 3600.0
HUB_BUILD_HOURS = BUILD_HOURS
MATERIALS = {
    "scrap_metal": {"name": "Металл", "price": 45, "weight": 0.2},
    "scrap_plate": {"name": "Пластины", "price": 90, "weight": 0.3},
    "electronics": {"name": "Электроника", "price": 250, "weight": 0.1},
    "fuelcell": {"name": "Топливные ячейки", "price": 160, "weight": 0.5},
    "propellant": {"name": "Ракетное топливо", "price": 420, "weight": 0.4},
    "warhead": {"name": "Боевые блоки", "price": 850, "weight": 0.8},
    "plasma_core": {"name": "Плазменные сердечники", "price": 1300, "weight": 0.9},
    "rail_core": {"name": "Рельсовые сердечники", "price": 1600, "weight": 1.0},
    "titanium": {"name": "Титан", "price": 900, "weight": 0.6},
    "composite": {"name": "Композит", "price": 1100, "weight": 0.7},
    "circuitry": {"name": "Микросхемы", "price": 1400, "weight": 0.2},
    "coolant": {"name": "Охлаждающая жидкость", "price": 720, "weight": 0.5},
    "advanced_alloy": {"name": "Прочный сплав", "price": 1900, "weight": 0.9},
}
FREIGHTER_COST = {"scrap_metal": 100, "scrap_plate": 20, "electronics": 5}
FREIGHTER_CAPACITY = 150.0
FREIGHTER_SPEED = 20.0
FREIGHTER_JUMP_SECONDS = 120.0
FREIGHTER_MIN_TRAVEL_SECONDS = 30.0
SECTOR_SIZE = 4000.0
SECTOR_GATE_MARGIN = 350.0


@dataclass(frozen=True)
class ModuleDefinition:
    id: str
    name: str
    category: str
    cost: dict
    build_hours: float
    active_power: float = 0.0
    passive_power: float = 0.0
    generation: float = 0.0
    fuel_per_hour: float = 0.0
    battery_capacity: float = 0.0
    inputs_per_hour: dict | None = None
    outputs_per_hour: dict | None = None


MODULES = {
    "solar_array": ModuleDefinition(
        "solar_array", "Solar array", "energy",
        {"scrap_metal": 30, "electronics": 5}, BUILD_HOURS, passive_power=0.5,
        generation=18),
    "fuel_reactor": ModuleDefinition(
        "fuel_reactor", "Fuel reactor", "energy",
        {"scrap_metal": 45, "electronics": 8}, BUILD_HOURS, passive_power=1.5,
        generation=48, fuel_per_hour=0.5),
    "battery": ModuleDefinition(
        "battery", "Accumulator", "energy",
        {"scrap_metal": 25, "electronics": 4}, BUILD_HOURS,
        passive_power=0.25, battery_capacity=120),
    "scrap_recycler": ModuleDefinition(
        "scrap_recycler", "Scrap recycler", "production",
        {"scrap_metal": 20, "electronics": 3}, BUILD_HOURS,
        active_power=5, passive_power=1,
        outputs_per_hour={"scrap_metal": 8}),
    "parts_assembler": ModuleDefinition(
        "parts_assembler", "Parts assembler", "production",
        {"scrap_metal": 35, "electronics": 6}, BUILD_HOURS,
        active_power=8, passive_power=1.5,
        inputs_per_hour={"scrap_metal": 6},
        outputs_per_hour={"scrap_plate": 2, "electronics": 0.5}),
    "cargo_bay": ModuleDefinition(
        "cargo_bay", "Storage bay", "logistics",
        {"scrap_metal": 20}, BUILD_HOURS, active_power=1, passive_power=0.5),
    "turret": ModuleDefinition(
        "turret", "Defense turret", "defense",
        {"scrap_metal": 30, "electronics": 4}, BUILD_HOURS,
        active_power=4, passive_power=1),
    "life_support": ModuleDefinition(
        "life_support", "Life support", "life_support",
        {"scrap_metal": 25, "electronics": 5}, BUILD_HOURS,
        active_power=3, passive_power=2),
    "research_lab": ModuleDefinition(
        "research_lab", "Research lab", "science_special",
        {"scrap_metal": 40, "electronics": 10}, BUILD_HOURS,
        active_power=7, passive_power=2),
    "ammo_press": ModuleDefinition(
        "ammo_press", "Ammunition press", "production",
        {"scrap_metal": 55, "scrap_plate": 15, "electronics": 8}, BUILD_HOURS,
        active_power=9, passive_power=2,
        inputs_per_hour={"scrap_metal": 5, "scrap_plate": 1,
                         "propellant": 2},
        outputs_per_hour={"warhead": 1.5, "electronics": 0.25}),
    "missile_forge": ModuleDefinition(
        "missile_forge", "Missile forge", "production",
        {"scrap_plate": 30, "electronics": 18, "warhead": 12}, BUILD_HOURS,
        active_power=12, passive_power=3,
        inputs_per_hour={"scrap_plate": 3, "electronics": 2,
                         "warhead": 2, "propellant": 4},
        outputs_per_hour={"missile_ammo": 2.0, "missile_heavy": 0.5}),
    "plasma_foundry": ModuleDefinition(
        "plasma_foundry", "Plasma foundry", "production",
        {"scrap_metal": 80, "electronics": 35, "plasma_core": 8}, BUILD_HOURS,
        active_power=14, passive_power=3,
        inputs_per_hour={"scrap_plate": 4, "electronics": 3,
                         "plasma_core": 2, "propellant": 3},
        outputs_per_hour={"missile_plasma": 1.0, "missile_cluster": 0.25}),
    "rail_foundry": ModuleDefinition(
        "rail_foundry", "Rail-core foundry", "production",
        {"scrap_metal": 100, "scrap_plate": 40, "electronics": 45,
         "rail_core": 10}, BUILD_HOURS,
        active_power=16, passive_power=4,
        inputs_per_hour={"scrap_plate": 5, "electronics": 4,
                         "rail_core": 2, "propellant": 2},
        outputs_per_hour={"missile_piercer": 0.75, "missile_emp": 0.5}),
    "weapon_assembler": ModuleDefinition(
        "weapon_assembler", "Weapon assembler", "production",
        {"scrap_metal": 90, "scrap_plate": 30, "electronics": 30}, BUILD_HOURS,
        active_power=15, passive_power=3,
        inputs_per_hour={"scrap_metal": 8, "scrap_plate": 4,
                         "electronics": 4},
        outputs_per_hour={"rail_core": 0.35, "plasma_core": 0.45}),
    "shipyard": ModuleDefinition(
        "shipyard", "Корабельная верфь", "shipbuilding",
        {"scrap_metal": 180, "scrap_plate": 90, "electronics": 45,
         "titanium": 30, "advanced_alloy": 15}, BUILD_HOURS,
        active_power=20, passive_power=4),
    "railgun_forge": ModuleDefinition(
        "railgun_forge", "Railgun ammunition forge", "production",
        {"scrap_metal": 120, "scrap_plate": 50, "electronics": 40,
         "rail_core": 15}, BUILD_HOURS,
        active_power=18, passive_power=4,
        inputs_per_hour={"scrap_metal": 6, "scrap_plate": 4,
                         "electronics": 3, "rail_core": 1,
                         "propellant": 2},
        outputs_per_hour={"railkinetic": 2.0, "railplasma": 0.6,
                          "railpiercer": 0.35, "rail_nuclear": 0.08}),
}


class Station:
    """One player-owned station and its serialized construction/power state."""

    def __init__(self, name="Outpost", sector=0, position=None, station_id=None):
        self.id = station_id or uuid.uuid4().hex
        self.name = str(name)
        self.sector = int(sector)
        self.position = list(position or (0, 0))
        self.has_hub = False
        self.hub_progress = 0.0
        self.resources = {}
        self.modules = []
        self.queue = []
        self.ship_queue = []
        self.energy_storage = 0.0
        self.script = ""
        self.script_log = []
        self._script_tick_elapsed = 0.0
        self._low_energy_active = False
        self._ship_completion_callback = None
        self.energy_status = {"generation": 0.0, "demand": 0.0,
                              "powered": 0, "offline": 0}

    def add_resources(self, item, amount):
        amount = float(amount)
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.resources[item] = float(self.resources.get(item, 0)) + amount

    def _enqueue(self, kind, definition_id=None, position=None):
        if kind == "hub":
            if self.has_hub or any(p["kind"] == "hub" for p in self.queue):
                raise ValueError("station already has, or is building, a hub")
            self.queue.append({"kind": "hub", "definition_id": None,
                               "progress": 0.0, "paid": False})
            return
        if not self.has_hub:
            raise ValueError("build a hub before installing modules")
        if definition_id not in MODULES:
            raise ValueError("unknown module: %s" % definition_id)
        self.queue.append({"kind": "module", "definition_id": definition_id,
                           "position": list(position or (0, 0)),
                           "progress": 0.0, "paid": False})

    def queue_hub(self):
        self._enqueue("hub")

    def queue_module(self, definition_id, position=(0, 0)):
        """Queue any module type at a free-form hub coordinate."""
        self._enqueue("module", definition_id, position)

    def ship_build_cost(self, ship_id):
        from ships_data import SHIPS_BY_ID
        ship = SHIPS_BY_ID.get(ship_id)
        if ship is None:
            raise ValueError("unknown ship: %s" % ship_id)
        cargo = float(ship.get("cargo_max", 0))
        fuel = float(ship.get("fuel_max", 100))
        scale = max(1.0, (cargo + fuel * 0.08) / 100.0)
        return {
            "scrap_metal": int(40 * scale),
            "scrap_plate": int(20 * scale),
            "electronics": int(12 * scale),
            "titanium": int(10 * scale),
            "composite": int(6 * scale),
            "circuitry": int(4 * scale),
            "coolant": int(3 * scale),
            "advanced_alloy": int(8 * scale),
        }

    def has_shipyard(self):
        return any(module.get("type") == "shipyard"
                   for module in self.modules)

    def queue_ship(self, ship_id):
        from ships_data import SHIPS_BY_ID
        if ship_id not in SHIPS_BY_ID:
            raise ValueError("unknown ship: %s" % ship_id)
        if not self.has_shipyard():
            raise ValueError("build a shipyard before building ships")
        if any(project.get("ship_id") == ship_id for project in self.ship_queue):
            raise ValueError("this ship is already being built")
        ship = SHIPS_BY_ID[ship_id]
        cost = self.ship_build_cost(ship_id)
        self.ship_queue.append({
            "ship_id": ship_id,
            "progress": 0.0,
            "build_hours": max(2.0, float(ship.get("price", 0)) / 35000.0),
            "paid": False,
            "cost": cost,
        })
        return "Ship queued: %s" % ship["name"]

    def set_module_position(self, module_id, x, y):
        for module in self.modules:
            if module["id"] == module_id:
                module["x"], module["y"] = float(x), float(y)
                return
        raise KeyError(module_id)

    def set_priority(self, module_id, priority):
        """Higher numbers receive power first; priorities are clamped 0..9."""
        priority = max(0, min(9, int(priority)))
        for module in self.modules:
            if module["id"] == module_id:
                module["priority"] = priority
                return
        raise KeyError(module_id)

    def _update_ship_queue(self, hours):
        if not self.ship_queue:
            return []
        completed = []
        if not self.has_shipyard():
            return completed
        for project in list(self.ship_queue):
            cost = project.get("cost", self.ship_build_cost(project["ship_id"]))
            if not project.get("paid", False):
                if any(self.resources.get(item, 0) < amount
                       for item, amount in cost.items()):
                    continue
                for item, amount in cost.items():
                    remaining = float(self.resources.get(item, 0)) - amount
                    if remaining:
                        self.resources[item] = remaining
                    else:
                        self.resources.pop(item, None)
                project["paid"] = True
            project["progress"] = float(project.get("progress", 0)) + hours
            if project["progress"] >= float(project.get("build_hours", 1)):
                completed.append(project["ship_id"])
        for ship_id in completed:
            self.ship_queue = [project for project in self.ship_queue
                               if project["ship_id"] != ship_id]
        return completed

    def _station_script_api(self):
        def build_module(module_type, x=None, y=None):
            count = len(self.modules) + sum(
                1 for project in self.queue if project["kind"] == "module")
            position = ((count % 4) * 120, (count // 4) * 100)
            if x is not None or y is not None:
                position = (0 if x is None else x, 0 if y is None else y)
            self.queue_module(str(module_type), position)
            return "Module queued: %s" % module_type

        def set_priority(index, priority):
            index = int(index)
            if index < 0 or index >= len(self.modules):
                raise ValueError("module index is out of range")
            self.set_priority(self.modules[index]["id"], priority)
            return "Priority updated"

        def move_module(index, x, y):
            index = int(index)
            if index < 0 or index >= len(self.modules):
                raise ValueError("module index is out of range")
            self.set_module_position(self.modules[index]["id"], x, y)
            return "Module moved"

        def resource(item):
            if item not in MATERIALS:
                raise ValueError("unknown resource: %s" % item)
            return float(self.resources.get(item, 0))

        def build_ship(ship_id):
            return self.queue_ship(str(ship_id))

        def ship_count(ship_id):
            from ships_data import SHIPS_BY_ID
            if ship_id not in SHIPS_BY_ID:
                raise ValueError("unknown ship: %s" % ship_id)
            return sum(1 for project in self.ship_queue
                       if project.get("ship_id") == ship_id)

        def log(message):
            self.script_log.append(str(message)[:240])
            self.script_log = self.script_log[-8:]

        return {
            "station.build_hub": self.queue_hub,
            "station.build_module": build_module,
            "station.build_ship": build_ship,
            "station.has_shipyard": self.has_shipyard,
            "station.ship_count": ship_count,
            "station.set_priority": set_priority,
            "station.move_module": move_module,
            "station.has_hub": lambda: self.has_hub,
            "station.resource": resource,
            "station.module_count": lambda: len(self.modules),
            "station.queue_count": lambda: len(self.queue),
            "station.energy_generation": lambda: self.energy_status["generation"],
            "station.energy_demand": lambda: self.energy_status["demand"],
            "station.log": log,
        }

    def _run_station_event(self, event, extra_api=None):
        if not self.script:
            return
        api = self._station_script_api()
        api.update(extra_api or {})
        try:
            run_station_script(self.script, api,
                               self.script_log, event=event, automatic=True)
        except StationScriptError as exc:
            self.script_log.append("Error (%s): %s" % (event, exc))
            self.script_log = self.script_log[-8:]

    @staticmethod
    def _project_cost(project):
        if project["kind"] == "hub":
            return HUB_COST
        return MODULES[project["definition_id"]].cost

    def _pay_project(self, project):
        cost = self._project_cost(project)
        if any(self.resources.get(item, 0) < amount
               for item, amount in cost.items()):
            return False
        for item, amount in cost.items():
            remaining = self.resources.get(item, 0) - amount
            if remaining:
                self.resources[item] = remaining
            else:
                self.resources.pop(item, None)
        project["paid"] = True
        return True

    def _finish_project(self, project):
        if project["kind"] == "hub":
            self.has_hub = True
            self.hub_progress = 1.0
            return
        definition = MODULES[project["definition_id"]]
        position = project.get("position", (0, 0))
        self.modules.append({"id": uuid.uuid4().hex, "type": definition.id,
                             "priority": 5, "x": float(position[0]),
                             "y": float(position[1]),
                             "operational": True})

    def _energy_step(self, hours):
        """Allocate power by priority, charging/discharging batteries."""
        installed = [(m, MODULES[m["type"]]) for m in self.modules
                     if m.get("type") in MODULES]
        solar = sum(d.generation for _, d in installed if d.id == "solar_array")
        reactors = [(m, d) for m, d in installed if d.fuel_per_hour > 0]
        reactor_available = sum(d.generation for _, d in reactors)
        fuel_needed = sum(d.fuel_per_hour for _, d in reactors) * hours
        fuel_available = float(self.resources.get("fuelcell", 0))
        if fuel_needed > fuel_available and fuel_needed:
            reactor_available *= fuel_available / fuel_needed
            fuel_needed = fuel_available

        generation = solar + reactor_available
        # A small emergency/tender generator lets a newly completed hub build
        # its first real power module instead of getting stuck at zero power.
        if generation <= 0:
            generation = 5.0
        batteries = [(m, d) for m, d in installed if d.battery_capacity > 0]
        capacity = sum(d.battery_capacity for _, d in batteries)
        self.energy_storage = min(capacity, max(0.0, self.energy_storage))
        hub_demand = 0.5 + 0.25 * len(self.modules) if self.has_hub else 0.0
        ordered = sorted(
            ((m, d) for m, d in installed
             if d.generation <= 0 and d.battery_capacity <= 0),
            key=lambda pair: (-int(pair[0].get("priority", 5)), pair[0]["id"]))
        always_on = sum(d.passive_power for _, d in installed
                        if d.generation > 0 or d.battery_capacity > 0)
        total_requested = hub_demand + always_on + sum(
            d.active_power + d.passive_power for _, d in ordered)

        available_energy = generation * hours + self.energy_storage
        fixed_energy = (hub_demand + always_on) * hours
        remaining = max(0.0, available_energy - fixed_energy)
        consumers = []
        for module, definition in ordered:
            amount = (definition.active_power + definition.passive_power) * hours
            powered = remaining + 1e-9 >= amount
            if powered:
                remaining -= amount
            consumers.append((module, definition, powered))

        used = fixed_energy + sum(
            (d.active_power + d.passive_power) * hours
            for _, d, powered in consumers if powered)
        if reactors and fuel_needed:
            self.resources["fuelcell"] = max(0.0, fuel_available - fuel_needed)
        for module, _, powered in consumers:
            module["operational"] = powered

        self.energy_status = {
            "generation": round(generation, 3),
            "demand": round(total_requested, 3),
            "powered": sum(1 for _, _, on in consumers if on),
            "offline": sum(1 for _, _, on in consumers if not on),
        }
        surplus = max(0.0, available_energy - used)
        construction_energy = min(surplus, 2.0 * hours)
        self.energy_storage = min(capacity, max(0.0, surplus - construction_energy))
        return construction_energy / (2.0 * hours) if hours else 0.0

    def _production_step(self, hours):
        """Run powered production modules for this part of an in-game hour.

        Recipe rates are expressed per hour. If a module lacks an input, it
        runs proportionally to the amount available instead of consuming a
        partial recipe and producing nothing.
        """
        if hours <= 0:
            return
        for module in self.modules:
            definition = MODULES.get(module.get("type"))
            if (definition is None or not module.get("operational", True)
                    or not definition.outputs_per_hour):
                continue

            inputs = definition.inputs_per_hour or {}
            run_fraction = 1.0
            for item, rate in inputs.items():
                needed = rate * hours
                if needed > 0:
                    available = max(0.0, float(self.resources.get(item, 0)))
                    run_fraction = min(run_fraction, available / needed)
            run_fraction = max(0.0, min(1.0, run_fraction))

            for item, rate in inputs.items():
                consumed = rate * hours * run_fraction
                if consumed:
                    remaining = max(0.0, float(self.resources.get(item, 0)) - consumed)
                    if remaining > 1e-12:
                        self.resources[item] = remaining
                    else:
                        self.resources.pop(item, None)
            for item, rate in definition.outputs_per_hour.items():
                produced = rate * hours * run_fraction
                if produced:
                    self.resources[item] = float(self.resources.get(item, 0)) + produced

    def production_rates(self, operational_only=True):
        """Return aggregate resource input/output rates in units per hour."""
        rates = {}
        for module in self.modules:
            definition = MODULES.get(module.get("type"))
            if definition is None:
                continue
            if operational_only and not module.get("operational", True):
                continue
            for item, rate in (definition.outputs_per_hour or {}).items():
                rates[item] = rates.get(item, 0.0) + rate
            for item, rate in (definition.inputs_per_hour or {}).items():
                rates[item] = rates.get(item, 0.0) - rate
        return {item: rate for item, rate in rates.items() if rate}

    def advance(self, game_seconds, script_api=None):
        """Advance station simulation; return seconds of construction progress."""
        remaining_seconds = max(0.0, float(game_seconds))
        progressed = 0.0
        while remaining_seconds > 0:
            step_seconds = min(3600.0, remaining_seconds)
            hours = step_seconds / 3600.0
            construction_factor = self._energy_step(hours) if self.has_hub else 1.0
            if self.has_hub:
                self._production_step(hours)
            low_energy = (self.has_hub and (
                self.energy_status["offline"] > 0
                or self.energy_status["generation"]
                < self.energy_status["demand"]))
            if low_energy and not self._low_energy_active:
                self._run_station_event("low_energy", script_api)
            self._low_energy_active = low_energy

            # Tick scripts run at most once per in-game hour. Large offline
            # advances are split into hourly steps above, so automation catches up.
            self._script_tick_elapsed += step_seconds
            if self._script_tick_elapsed >= 3600.0:
                self._script_tick_elapsed %= 3600.0
                self._run_station_event("tick", script_api)
            completed_ships = self._update_ship_queue(hours)
            for ship_id in completed_ships:
                if getattr(self, "_ship_completion_callback", None):
                    self._ship_completion_callback(ship_id)
            if self.queue:
                project = self.queue[0]
                if not project["paid"] and not self._pay_project(project):
                    remaining_seconds -= step_seconds
                    continue
                if project["kind"] == "hub":
                    construction_factor = 1.0
                    build_hours = HUB_BUILD_HOURS
                else:
                    build_hours = MODULES[project["definition_id"]].build_hours
                project["progress"] += hours * construction_factor
                progressed += step_seconds * construction_factor
                if project["kind"] == "hub":
                    self.hub_progress = min(1.0, project["progress"] / build_hours)
                if project["progress"] + 1e-9 >= build_hours:
                    self._finish_project(project)
                    self.queue.pop(0)
            remaining_seconds -= step_seconds
        return progressed

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "sector": self.sector,
            "position": list(self.position), "has_hub": self.has_hub,
            "hub_progress": self.hub_progress,
            "resources": dict(self.resources),
            "modules": [dict(m) for m in self.modules],
            "queue": [dict(p) for p in self.queue],
            "ship_queue": [dict(p) for p in self.ship_queue],
            "energy_storage": self.energy_storage,
            "script": self.script,
            "script_log": list(self.script_log[-8:]),
        }

    @classmethod
    def from_dict(cls, data):
        station = cls(data.get("name", "Outpost"), data.get("sector", 0),
                      data.get("position", (0, 0)), data.get("id"))
        station.has_hub = bool(data.get("has_hub", False))
        station.hub_progress = max(0.0, min(1.0, float(data.get("hub_progress", 0))))
        station.resources = {str(k): max(0.0, float(v))
                             for k, v in data.get("resources", {}).items()}
        station.modules = []
        for raw in data.get("modules", []):
            if raw.get("type") not in MODULES:
                continue
            module = dict(raw)
            module["priority"] = max(0, min(9, int(module.get("priority", 5))))
            module["x"] = float(module.get("x", 0))
            module["y"] = float(module.get("y", 0))
            station.modules.append(module)
        station.queue = []
        for raw in data.get("queue", []):
            kind, definition_id = raw.get("kind"), raw.get("definition_id")
            if kind == "hub" and not station.has_hub:
                station.queue.append({"kind": "hub", "definition_id": None,
                                      "progress": max(0.0, float(raw.get("progress", 0))),
                                      "paid": bool(raw.get("paid", False))})
            elif kind == "module" and definition_id in MODULES and station.has_hub:
                station.queue.append({"kind": "module", "definition_id": definition_id,
                                      "position": list(raw.get("position", (0, 0))),
                                      "progress": max(0.0, float(raw.get("progress", 0))),
                                      "paid": bool(raw.get("paid", False))})
        station.ship_queue = []
        for raw in data.get("ship_queue", []):
            if not isinstance(raw, dict):
                continue
            ship_id = raw.get("ship_id")
            try:
                from ships_data import SHIPS_BY_ID
                if ship_id not in SHIPS_BY_ID:
                    continue
                cost = raw.get("cost") if isinstance(raw.get("cost"), dict) else station.ship_build_cost(ship_id)
                station.ship_queue.append({
                    "ship_id": ship_id,
                    "progress": max(0.0, float(raw.get("progress", 0))),
                    "build_hours": max(0.1, float(raw.get("build_hours", 1))),
                    "paid": bool(raw.get("paid", False)),
                    "cost": {str(k): max(0.0, float(v)) for k, v in cost.items()},
                })
            except (TypeError, ValueError):
                continue
        station.energy_storage = max(0.0, float(data.get("energy_storage", 0)))
        station.script = str(data.get("script", ""))[:5000]
        station.script_log = [str(line)[:240]
                              for line in data.get("script_log", [])[-8:]]
        return station


class StationNetwork:
    """Collection helper with persistence and offline elapsed-time support."""

    def __init__(self, stations=None, last_updated=None, sector_graph=None,
                 market_stations=None, systems=None):
        self.stations = list(stations or [])
        self.last_updated = float(last_updated if last_updated is not None else time.time())
        self.freighters = []
        self.sector_graph = sector_graph
        self.market_stations = list(market_stations or [])
        self.systems = systems

    def _station_script_api(self, station):
        """Return the logistics commands available to a station script."""
        def build_freighter():
            missing = ["%s: %g" % (item, amount - station.resources.get(item, 0))
                       for item, amount in FREIGHTER_COST.items()
                       if station.resources.get(item, 0) < amount]
            if missing:
                raise ValueError("not enough resources to build freighter (" +
                                 ", ".join(missing) + ")")
            for item, amount in FREIGHTER_COST.items():
                station.resources[item] -= amount
            freighter = {
                "id": uuid.uuid4().hex,
                "station_id": station.id,
                "destination_id": None,
                "resource": None,
                "cargo": 0.0,
                "travel_remaining": 0.0,
            }
            self.freighters.append(freighter)
            return "Freighter built"

        def available_freighters():
            return sum(1 for ship in self.freighters
                       if ship.get("station_id") == station.id
                       and ship.get("destination_id") is None
                       and ship.get("trip_stage") is None)

        def buy_freighter(item, amount):
            if item not in MATERIALS:
                raise ValueError("unknown resource: %s" % item)
            amount = float(amount)
            if amount <= 0:
                raise ValueError("amount must be positive")
            if amount * MATERIALS[item]["weight"] > FREIGHTER_CAPACITY:
                raise ValueError("shipment exceeds freighter capacity")
            freighter = next((ship for ship in self.freighters
                              if ship.get("station_id") == station.id
                              and ship.get("destination_id") is None
                              and ship.get("trip_stage") is None), None)
            if freighter is None:
                raise ValueError("no idle freighter at this station")
            if not self.market_stations:
                raise ValueError("no NPC stations are available for purchases")
            if self.systems is None:
                raise ValueError(
                    "player credits are not connected to the station network")

            market = min(
                self.market_stations,
                key=lambda row: self._route_travel_seconds(
                    station.sector, station.position,
                    row["sector"], row["position"]))
            one_way = self._route_travel_seconds(
                station.sector, station.position,
                market["sector"], market["position"])
            cost = MATERIALS[item]["price"] * amount
            if self.systems.money < cost:
                raise ValueError("not enough credits to buy %s" % item)

            self.systems.money -= cost
            freighter.update({
                "destination_id": station.id,
                "trip_stage": "to_market",
                "market_name": market["name"],
                "resource": item,
                "cargo": 0.0,
                "purchase_amount": amount,
                "purchase_cost": cost,
                "return_travel_seconds": one_way,
                "travel_remaining": one_way,
            })
            return "Freighter buying %g %s at %s" % (
                amount, item, market["name"])

        def credits():
            return float(self.systems.money) if self.systems is not None else 0.0

        return {
            "freighter.build": build_freighter,
            "freighter.available": available_freighters,
            "freighter.buy": buy_freighter,
            "freighter.send": buy_freighter,
            "player.credits": credits,
        }

    def _advance_freighters(self, game_seconds):
        for ship in self.freighters:
            if ship.get("destination_id") is None:
                continue
            elapsed = max(0.0, float(game_seconds))
            while True:
                remaining = max(0.0, float(ship.get("travel_remaining", 0)))
                if remaining > elapsed:
                    ship["travel_remaining"] = remaining - elapsed
                    break
                elapsed -= remaining
                if ship.get("trip_stage") == "to_market":
                    ship.update({
                        "trip_stage": "returning",
                        "cargo": float(ship.get("purchase_amount", 0)),
                        "travel_remaining": float(
                            ship.get("return_travel_seconds", 0)),
                    })
                    if elapsed <= 0:
                        break
                    continue

                destination_id = ship.get("destination_id")
                destination = next((station for station in self.stations
                                    if station.id == destination_id), None)
                if destination is not None:
                    destination.add_resources(ship.get("resource"),
                                              ship.get("cargo", 0))
                ship.update({"station_id": destination_id,
                             "destination_id": None,
                             "resource": None,
                             "cargo": 0.0,
                             "travel_remaining": 0.0,
                             "trip_stage": None})
                break

    @staticmethod
    def _distance_to_nearest_gate(position):
        edge = SECTOR_SIZE - SECTOR_GATE_MARGIN
        gates = ((SECTOR_GATE_MARGIN, SECTOR_GATE_MARGIN),
                 (edge, SECTOR_GATE_MARGIN),
                 (SECTOR_GATE_MARGIN, edge), (edge, edge))
        x, y = position
        return min(math.hypot(x - gx, y - gy) for gx, gy in gates)

    def _sector_hops(self, start, destination):
        if start == destination:
            return 0
        if self.sector_graph:
            pending = [(start, 0)]
            visited = {start}
            while pending:
                sector, hops = pending.pop(0)
                for neighbor in self.sector_graph.get(sector, ()):
                    if neighbor == destination:
                        return hops + 1
                    if neighbor not in visited:
                        visited.add(neighbor)
                        pending.append((neighbor, hops + 1))
        # Older saves or standalone callers may not supply the galaxy graph.
        return max(1, abs(int(start) - int(destination)))

    def _route_travel_seconds(self, origin_sector, origin_position,
                              destination_sector, destination_position):
        hops = self._sector_hops(origin_sector, destination_sector)
        if hops == 0:
            distance = math.hypot(
                origin_position[0] - destination_position[0],
                origin_position[1] - destination_position[1])
        else:
            distance = (self._distance_to_nearest_gate(origin_position)
                        + self._distance_to_nearest_gate(destination_position)
                        + max(0, hops - 1) * SECTOR_SIZE)
        return max(FREIGHTER_MIN_TRAVEL_SECONDS,
                   distance / FREIGHTER_SPEED
                   + hops * FREIGHTER_JUMP_SECONDS)

    def _freighter_travel_seconds(self, origin, destination):
        return self._route_travel_seconds(
            origin.sector, origin.position,
            destination.sector, destination.position)

    def add_station(self, name="Outpost", sector=0, position=None):
        station = Station(name, sector, position)
        self.stations.append(station)
        return station

    def advance(self, game_seconds):
        remaining = max(0.0, float(game_seconds))
        while remaining > 0:
            step = min(3600.0, remaining)
            self._advance_freighters(step)
            for station in self.stations:
                if self.systems is not None:
                    def ship_completed(ship_id, systems=self.systems):
                        systems.add_captured_ship(ship_id)
                    station._ship_completion_callback = ship_completed
                station.advance(step, self._station_script_api(station))
            remaining -= step

    def to_dict(self, timestamp=None):
        self.last_updated = float(timestamp if timestamp is not None else time.time())
        return {"last_updated": self.last_updated,
                "stations": [station.to_dict() for station in self.stations],
                "freighters": [dict(ship) for ship in self.freighters]}

    @classmethod
    def from_dict(cls, data, now=None, sector_graph=None,
                  market_stations=None, systems=None):
        now = float(now if now is not None else time.time())
        if not isinstance(data, dict):
            return cls(sector_graph=sector_graph,
                       market_stations=market_stations, systems=systems)
        saved_at = float(data.get("last_updated", now))
        network = cls([Station.from_dict(row) for row in data.get("stations", [])
                       if isinstance(row, dict)], now, sector_graph,
                      market_stations, systems)
        station_ids = {station.id for station in network.stations}
        for raw in data.get("freighters", []):
            if not isinstance(raw, dict) or raw.get("station_id") not in station_ids:
                continue
            ship = dict(raw)
            if ship.get("destination_id") not in station_ids:
                ship.update({"destination_id": None, "resource": None,
                             "cargo": 0.0, "travel_remaining": 0.0,
                             "trip_stage": None})
            if ship.get("resource") not in MATERIALS:
                ship.update({"destination_id": None, "resource": None,
                             "cargo": 0.0, "travel_remaining": 0.0,
                             "trip_stage": None})
            if ship.get("trip_stage") not in (None, "to_market", "returning"):
                ship.update({"destination_id": None, "resource": None,
                             "cargo": 0.0, "travel_remaining": 0.0,
                             "trip_stage": None})
            ship["cargo"] = max(0.0, float(ship.get("cargo", 0)))
            ship["travel_remaining"] = max(
                0.0, float(ship.get("travel_remaining", 0)))
            network.freighters.append(ship)
        offline_seconds = max(0.0, now - saved_at)
        if offline_seconds:
            network.advance(offline_seconds)
        return network
