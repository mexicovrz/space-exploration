import unittest

import combat
from data import (AMMO_BY_ID, PARTS_BY_ID, RAILGUN_AMMO, RAIL_AMMO_DEF)
from ship import PartInstance, ShipSystems
from station import Station, StationNetwork


RAIL_IDS = [row[0] for row in RAIL_AMMO_DEF]


class RailgunDataTests(unittest.TestCase):
    def test_ammo_and_railgun_part_are_defined(self):
        for ammo_id in RAIL_IDS:
            self.assertIn(ammo_id, RAILGUN_AMMO)
            self.assertIn(ammo_id, AMMO_BY_ID)

        part = PARTS_BY_ID["railgun_w"]
        self.assertEqual(part["tier_for"], "laser_w")
        self.assertEqual(part["effects"]["is_railgun"], 1)

    def test_nuclear_shell_has_area_damage_and_emp(self):
        nuclear = RAILGUN_AMMO["rail_nuclear"]
        self.assertTrue(nuclear["nuclear"])
        self.assertGreater(nuclear["damage"], RAILGUN_AMMO["railkinetic"]["damage"])
        self.assertGreater(nuclear["blast_radius"], 0)
        self.assertGreater(nuclear["emp_duration"], 0)


class RailgunShipTests(unittest.TestCase):
    def setUp(self):
        self.systems = ShipSystems()
        slot = self.systems.systems["weapon"].slots[0]
        slot.part = PartInstance("railgun_w")

    def test_load_unload_and_fire(self):
        self.assertTrue(self.systems.has_railgun)
        self.assertTrue(self.systems.add_ammo("railplasma", 2))
        self.assertTrue(self.systems.load_rail_ammo("railplasma"))
        self.assertEqual(self.systems.ammo.get("railplasma"), 1)
        self.assertEqual(self.systems.loaded_rail_count, 1)

        self.assertTrue(self.systems.unload_rail_ammo())
        self.assertEqual(self.systems.ammo.get("railplasma"), 2)
        self.assertEqual(self.systems.loaded_rail_count, 0)

        self.assertTrue(self.systems.load_rail_ammo("railplasma"))
        self.assertEqual(self.systems.fire_loaded_rail(), "railplasma")
        self.assertFalse(self.systems.has_loaded_rail)

    def test_loaded_shell_survives_save_roundtrip(self):
        self.systems.add_ammo("rail_nuclear", 1)
        self.systems.load_rail_ammo("rail_nuclear")
        saved = self.systems.to_dict()

        restored = ShipSystems()
        restored.apply_dict(saved, StationNetwork())
        self.assertEqual(restored.loaded_rail, {0: "rail_nuclear"})
        self.assertTrue(restored.has_loaded_rail)

    def test_removing_railgun_returns_shell_to_hold(self):
        self.systems.add_ammo("railkinetic", 1)
        self.systems.load_rail_ammo("railkinetic")
        self.systems.systems["weapon"].slots[0].part = None
        self.systems._sync_loaded_rail()
        self.assertEqual(self.systems.ammo.get("railkinetic"), 1)


class RailgunCombatTests(unittest.TestCase):
    def test_nuclear_shell_damages_area_and_disables_weapons(self):
        target = combat.NPCShip("patrol", 100, 0)
        near = combat.NPCShip("patrol", 150, 0)
        far = combat.NPCShip("patrol", 1000, 0)
        npcs = [target, near, far]

        killed = combat.fire_railgun((0, 0), target, "rail_nuclear", npcs)

        self.assertIn(target, killed)
        self.assertLess(near.hull_hp, near.hull_hp_max)
        self.assertEqual(near.emp_timer, 4.0)
        self.assertEqual(far.hull_hp, far.hull_hp_max)

    def test_piercing_shell_hits_several_targets_in_line(self):
        targets = [combat.NPCShip("pirate", 100 * i, 0) for i in range(1, 5)]
        killed = combat.fire_railgun((0, 0), targets[0], "railpiercer", targets)
        self.assertEqual(killed, targets[:3])
        self.assertFalse(targets[3].dead)


class RailgunStationTests(unittest.TestCase):
    def test_forge_produces_nuclear_ammo(self):
        station = Station("Forge")
        station.has_hub = True
        station.modules = [
            {"id": "solar1", "type": "solar_array", "priority": 5},
            {"id": "solar2", "type": "solar_array", "priority": 5},
            {"id": "forge", "type": "railgun_forge", "priority": 5},
        ]
        for item, amount in {"scrap_metal": 6, "scrap_plate": 4,
                             "electronics": 3, "rail_core": 1,
                             "propellant": 2}.items():
            station.add_resources(item, amount)

        station.advance(3600)
        self.assertAlmostEqual(station.resources.get("rail_nuclear", 0), 0.08)
        self.assertAlmostEqual(station.resources.get("railkinetic", 0), 2.0)

    def test_script_can_take_ammo_from_station(self):
        station = Station("Forge")
        station.add_resources("rail_nuclear", 2)
        station.script = 'player.take_ammo("rail_nuclear", 1)'
        network = StationNetwork([station])
        network.systems = ShipSystems()

        ok, message = network.run_script(station.id)
        self.assertTrue(ok, message)
        self.assertEqual(network.systems.ammo.get("rail_nuclear"), 1)
        self.assertAlmostEqual(station.resources["rail_nuclear"], 1)


class RailgunScriptProductionTests(unittest.TestCase):
    FORGE_COST = {"scrap_metal": 75, "scrap_plate": 50,
                  "electronics": 37.5, "rail_core": 12.5,
                  "propellant": 25}

    def _forge_station(self):
        station = Station("Forge")
        station.has_hub = True
        station.modules = [
            {"id": "forge", "type": "railgun_forge", "priority": 5,
             "operational": True},
        ]
        for item, amount in self.FORGE_COST.items():
            station.add_resources(item, amount)
        return station

    def test_produce_railgun_ammo_consumes_scaled_recipe(self):
        station = self._forge_station()

        self.assertEqual(station.produce_railgun_ammo("nuclear"), 1)

        self.assertAlmostEqual(station.resources.get("rail_nuclear", 0), 1.0)
        for item in self.FORGE_COST:
            self.assertAlmostEqual(station.resources.get(item, 0), 0.0)

    def test_script_can_call_bare_produce_railgun_ammo(self):
        station = self._forge_station()
        station.script = 'produce_railgun_ammo("nuclear")'
        network = StationNetwork([station])

        ok, message = network.run_script(station.id)

        self.assertTrue(ok, message)
        self.assertAlmostEqual(station.resources.get("rail_nuclear", 0), 1.0)

    def test_script_accepts_unquoted_shell_name(self):
        station = self._forge_station()
        station.script = 'produce_railgun_ammo(nuclear)'
        network = StationNetwork([station])

        ok, message = network.run_script(station.id)

        self.assertTrue(ok, message)
        self.assertAlmostEqual(station.resources.get("rail_nuclear", 0), 1.0)

    def test_production_requires_forge_and_materials(self):
        station = self._forge_station()
        station.modules = []

        with self.assertRaisesRegex(ValueError, "railgun_forge"):
            station.produce_railgun_ammo("railkinetic")

        station = self._forge_station()
        with self.assertRaisesRegex(ValueError, "not enough resources"):
            station.produce_railgun_ammo("rail_nuclear", 2)


if __name__ == "__main__":
    unittest.main()
