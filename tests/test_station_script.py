import unittest

from station import Station, StationNetwork
from station_script import run_station_script, StationScriptError


class StationScriptTests(unittest.TestCase):
    def test_variables_conditions_and_bounded_loops(self):
        calls = []
        run_station_script(
            "count = 0\n"
            "for item in range(3):\n"
            "    count += 1\n"
            "if count == 3:\n"
            "    station.set_priority(0, 9)\n",
            {"station.set_priority":
             lambda index, value: calls.append((index, value))},
        )
        self.assertEqual(calls, [(0, 9)])

    def test_rejects_python_imports_and_attribute_access(self):
        with self.assertRaises(StationScriptError):
            run_station_script("import os", {})
        with self.assertRaises(StationScriptError):
            run_station_script("(1).__class__", {})
        with self.assertRaises(StationScriptError):
            run_station_script("__import__('os')", {})
        with self.assertRaisesRegex(StationScriptError, "finite"):
            run_station_script('station.log(float("inf"))',
                               {"station.log": lambda _value: None})

    def test_only_freighter_buy_and_send_methods_are_allowed(self):
        calls = []
        api = {
            "freighter.buy": lambda item, count: calls.append(("buy", item, count)),
            "freighter.send": lambda item, count: calls.append(("send", item, count)),
        }
        run_station_script(
            'freighter.buy("scrap_metal", 50)\n'
            'freighter.send("electronics", 2)\n', api)
        self.assertEqual(calls, [
            ("buy", "scrap_metal", 50), ("send", "electronics", 2)])

        run_station_script('buy_freighter("electronics", 3)', api)
        run_station_script('send_freighter(1, "fuelcell", 2)', api)
        self.assertEqual(calls[-2:], [
            ("buy", "electronics", 3), ("send", "fuelcell", 2)])

        for script in ("freighter.fly()", "other.buy()",
                       "freighter.buy.__call__()"):
            with self.subTest(script=script), self.assertRaises(StationScriptError):
                run_station_script(script, api)

    def test_event_handlers_only_run_for_the_matching_event(self):
        calls = []
        script = (
            'station.log("manual")\n'
            'on tick:\n'
            '    station.log("tick")\n'
            'on low_energy: # comment is allowed\n'
            '    station.log("low")\n'
        )
        api = {"station.log": calls.append}
        run_station_script(script, api, automatic=True, event="low_energy")
        self.assertEqual(calls, ["low"])

        calls.clear()
        run_station_script(script, api)
        self.assertEqual(calls, ["manual"])

    def test_unknown_event_is_rejected(self):
        with self.assertRaisesRegex(StationScriptError, "unknown event"):
            run_station_script("on pirates:\n    pass", {},
                               automatic=True, event="pirates")

    def test_python_like_builtins_fstrings_and_safe_indexing(self):
        calls = []
        run_station_script(
            'prices = {"metal": 45, "plate": 90}\n'
            'items = ["scrap_metal", "scrap_plate"]\n'
            'count = sum([1, 2, 3])\n'
            'if count == 6 and prices["metal"] < prices["plate"]:\n'
            '    station.log(f"{items[0]} costs {prices[\'metal\']}")\n',
            {"station.log": calls.append})
        self.assertEqual(calls, ["scrap_metal costs 45"])

    def test_completion_event_can_inspect_finished_project(self):
        station = Station("Scripted")
        station.script = (
            "on project_complete:\n"
            "    station.log(station.last_completed_project())\n")
        station.queue_hub()
        for item, amount in {"scrap_metal": 300, "scrap_plate": 100,
                             "electronics": 20}.items():
            station.add_resources(item, amount)

        station.advance(1)

        self.assertTrue(station.has_hub)
        self.assertEqual(station.script_log, ["hub"])

    def test_ship_completion_event_can_inspect_ship_id(self):
        from ships_data import SHIPS_BY_ID

        station = Station("Shipyard")
        station.modules = [{"id": "yard", "type": "shipyard",
                            "priority": 5, "operational": False}]
        station.script = (
            "on ship_complete:\n"
            "    station.log(station.last_completed_ship())\n")
        ship_id = next(iter(SHIPS_BY_ID))
        station.queue_ship(ship_id)
        station.ship_queue[0].update({"paid": True, "build_hours": 0.1})

        station.advance(3600)

        self.assertEqual(station.script_log, [ship_id])

    def test_manual_network_script_has_freighter_and_player_api(self):
        station = Station("Scripted")
        station.script = (
            'station.set_name("Automated")\n'
            'station.log(player.credits())\n'
            'if player.has_credits(100):\n'
            '    freighter.build()\n')
        station.resources.update({"scrap_metal": 100, "scrap_plate": 20,
                                  "electronics": 5})
        wallet = type("Wallet", (), {"money": 10000})()
        network = StationNetwork([station], systems=wallet)

        result = network.run_script(station.id)

        self.assertTrue(result[0])
        self.assertEqual(station.name, "Automated")
        self.assertEqual(station.script_log, ["10000.0"])
        self.assertEqual(len(network.freighters), 1)

    def test_station_script_is_saved(self):
        station = Station("Scripted")
        station.script = 'station.log("hello")'
        restored = Station.from_dict(station.to_dict())
        self.assertEqual(restored.script, station.script)


if __name__ == "__main__":
    unittest.main()
