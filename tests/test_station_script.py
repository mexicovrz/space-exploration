import unittest

from station import Station
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

    def test_station_script_is_saved(self):
        station = Station("Scripted")
        station.script = 'station.log("hello")'
        restored = Station.from_dict(station.to_dict())
        self.assertEqual(restored.script, station.script)


if __name__ == "__main__":
    unittest.main()
