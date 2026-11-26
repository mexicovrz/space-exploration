import unittest

from station import HUB_COST, Station, StationNetwork


class StationTests(unittest.TestCase):
    def test_hub_stalls_without_materials_then_builds(self):
        station = Station("Foundry")
        station.queue_hub()
        station.advance(24 * 3600)
        self.assertFalse(station.has_hub)
        self.assertEqual(station.queue[0]["progress"], 0)

        for item, amount in HUB_COST.items():
            station.add_resources(item, amount)
        station.advance(0.999)
        self.assertFalse(station.has_hub)
        station.advance(0.001)
        self.assertTrue(station.has_hub)
        self.assertEqual(station.queue, [])
        self.assertEqual(station.hub_progress, 1)

    def test_modules_require_hub_and_priority_controls_power(self):
        station = Station()
        with self.assertRaises(ValueError):
            station.queue_module("life_support")

        station.has_hub = True
        station.modules = [
            {"id": "solar", "type": "solar_array", "priority": 5},
            {"id": "high", "type": "parts_assembler", "priority": 9},
            {"id": "low", "type": "research_lab", "priority": 1},
        ]
        station.advance(3600)
        self.assertTrue(station.modules[1]["operational"])
        self.assertFalse(station.modules[2]["operational"])
        self.assertEqual(station.energy_status["offline"], 1)

    def test_module_queue_progresses_with_surplus_power(self):
        station = Station()
        station.has_hub = True
        station.modules = [{"id": "solar", "type": "solar_array",
                            "priority": 5, "x": 0, "y": 0}]
        station.queue_module("cargo_bay", position=(120, -40))
        for item, amount in {"scrap_metal": 20}.items():
            station.add_resources(item, amount)
        station.advance(1)
        self.assertEqual(station.queue, [])
        self.assertEqual(station.modules[-1]["type"], "cargo_bay")
        self.assertEqual((station.modules[-1]["x"], station.modules[-1]["y"]),
                         (120, -40))

    def test_powered_recycler_produces_metal(self):
        station = Station()
        station.has_hub = True
        station.modules = [
            {"id": "solar", "type": "solar_array", "priority": 5},
            {"id": "recycler", "type": "scrap_recycler", "priority": 5},
        ]

        station.advance(3600)

        self.assertAlmostEqual(station.resources["scrap_metal"], 8)
        self.assertTrue(station.modules[1]["operational"])

    def test_assembler_consumes_metal_and_produces_materials(self):
        station = Station()
        station.has_hub = True
        station.resources["scrap_metal"] = 12
        station.modules = [
            {"id": "solar", "type": "solar_array", "priority": 5},
            {"id": "assembler", "type": "parts_assembler", "priority": 5},
        ]

        station.advance(3600)

        self.assertAlmostEqual(station.resources["scrap_metal"], 6)
        self.assertAlmostEqual(station.resources["scrap_plate"], 2)
        self.assertAlmostEqual(station.resources["electronics"], 0.5)
        self.assertEqual(station.production_rates(), {
            "scrap_metal": -6, "scrap_plate": 2, "electronics": 0.5,
        })

    def test_assembler_scales_output_to_available_input(self):
        station = Station()
        station.has_hub = True
        station.resources["scrap_metal"] = 3
        station.modules = [
            {"id": "solar", "type": "solar_array", "priority": 5},
            {"id": "assembler", "type": "parts_assembler", "priority": 5},
        ]

        station.advance(3600)

        self.assertNotIn("scrap_metal", station.resources)
        self.assertAlmostEqual(station.resources["scrap_plate"], 1)
        self.assertAlmostEqual(station.resources["electronics"], 0.25)

    def test_unpowered_production_module_does_not_run(self):
        station = Station()
        station.has_hub = True
        station.resources["scrap_metal"] = 12
        station.modules = [
            {"id": "assembler", "type": "parts_assembler", "priority": 5},
        ]

        station.advance(3600)

        self.assertFalse(station.modules[0]["operational"])
        self.assertEqual(station.resources, {"scrap_metal": 12})

    def test_roundtrip_and_offline_construction(self):
        station = Station("Remote", sector=3, position=(1234, 567))
        station.has_hub = True
        station.modules = [{"id": "solar", "type": "solar_array",
                            "priority": 5, "x": 0, "y": 0}]
        station.queue_module("cargo_bay")
        station.queue[0]["paid"] = True
        network = StationNetwork([station], last_updated=1000)

        saved = network.to_dict(timestamp=1000)
        loaded = StationNetwork.from_dict(saved, now=1000 + 6 * 3600)
        self.assertEqual(loaded.stations[0].sector, 3)
        self.assertEqual(loaded.stations[0].position, [1234, 567])
        self.assertEqual(loaded.stations[0].modules[-1]["type"], "cargo_bay")
        self.assertEqual(loaded.stations[0].queue, [])

    def test_low_energy_handler_runs_once_until_energy_recovers(self):
        station = Station()
        station.has_hub = True
        station.modules = [{"id": "assembler", "type": "parts_assembler",
                            "priority": 1, "x": 0, "y": 0}]
        station.script = (
            "on low_energy:\n"
            "    station.set_priority(0, 9)\n"
            '    station.log("power adjusted")\n'
        )

        station.advance(1)
        self.assertEqual(station.modules[0]["priority"], 9)
        self.assertEqual(station.script_log, ["power adjusted"])

        station.advance(1)
        self.assertEqual(station.script_log, ["power adjusted"])

    def test_tick_handler_runs_automatically(self):
        station = Station()
        station.script = "on tick:\n    station.build_hub()\n"
        station.advance(3600)
        self.assertEqual(len(station.queue), 1)
        self.assertEqual(station.queue[0]["kind"], "hub")

    def test_station_scripts_build_and_dispatch_freighters(self):
        origin = Station("Origin", sector=0, position=(350, 350))
        origin.resources = {
            "scrap_metal": 150,
            "scrap_plate": 20,
            "electronics": 5,
        }
        wallet = type("Wallet", (), {"money": 10000})()
        origin.script = (
            "on tick:\n"
            "    if freighter.available() == 0:\n"
            "        freighter.build()\n"
            "    else:\n"
            '        freighter.buy("scrap_metal", 50)\n'
        )
        network = StationNetwork(
            [origin], last_updated=100,
            market_stations=[{"name": "Nearby Market", "sector": 0,
                              "position": [1000, 350]}],
            systems=wallet)

        network.advance(3600)
        self.assertEqual(network.freighters[0]["station_id"], origin.id)
        self.assertEqual(origin.resources["scrap_metal"], 50)

        network.advance(3600)
        self.assertEqual(network.freighters[0]["trip_stage"], "to_market")
        self.assertEqual(network.freighters[0]["market_name"], "Nearby Market")
        self.assertEqual(wallet.money, 7750)
        self.assertEqual(origin.resources.get("scrap_metal", 0), 50)

        network = StationNetwork.from_dict(
            network.to_dict(timestamp=100), now=100,
            market_stations=network.market_stations, systems=wallet)

        network.advance(32.5)
        self.assertEqual(network.freighters[0]["trip_stage"], "returning")
        self.assertEqual(network.freighters[0]["cargo"], 50)
        self.assertEqual(network.stations[0].resources.get("scrap_metal", 0), 50)
        network.advance(32.5)
        restored_origin = network.stations[0]
        self.assertEqual(restored_origin.resources["scrap_metal"], 100)
        self.assertEqual(network.freighters[0]["station_id"], restored_origin.id)
        self.assertEqual(network.freighters[0]["destination_id"], None)

    def test_freighter_travel_is_saved_and_resumes(self):
        origin = Station("Origin")
        destination = Station("Destination")
        origin.resources["scrap_metal"] = 50
        network = StationNetwork([origin, destination], last_updated=100)
        network.freighters.append({
            "id": "freighter-1", "station_id": origin.id,
            "destination_id": destination.id, "resource": "scrap_metal",
            "cargo": 50, "travel_remaining": 200,
        })

        restored = StationNetwork.from_dict(network.to_dict(timestamp=100), now=250)
        self.assertEqual(restored.stations[1].resources.get("scrap_metal", 0), 0)
        self.assertEqual(restored.freighters[0]["travel_remaining"], 50)
        restored.advance(50)
        self.assertEqual(restored.stations[1].resources["scrap_metal"], 50)

    def test_freighter_travel_time_depends_on_station_distance(self):
        origin = Station("Origin", sector=0, position=(500, 500))
        nearby = Station("Nearby", sector=0, position=(1000, 500))
        distant = Station("Distant", sector=0, position=(3500, 3500))
        network = StationNetwork([origin, nearby, distant])

        nearby_time = network._freighter_travel_seconds(origin, nearby)
        distant_time = network._freighter_travel_seconds(origin, distant)
        self.assertEqual(nearby_time, 30)
        self.assertGreater(distant_time, nearby_time)

    def test_cross_sector_travel_uses_shortest_gate_route(self):
        origin = Station("Origin", sector=0, position=(350, 350))
        destination = Station("Destination", sector=2, position=(3650, 3650))
        graph = {0: [1], 1: [0, 2], 2: [1], 3: [0, 2]}
        network = StationNetwork([origin, destination], sector_graph=graph)

        # One intermediate sector costs one sector traversal plus two jumps.
        self.assertEqual(network._freighter_travel_seconds(origin, destination), 440)

        graph[0].append(2)
        graph[2].append(0)
        self.assertEqual(network._freighter_travel_seconds(origin, destination), 120)

if __name__ == "__main__":
    unittest.main()
