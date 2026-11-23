import unittest

import localization


class StationLocalizationTests(unittest.TestCase):
    def tearDown(self):
        localization.set_language("ru")

    def test_station_ui_and_marker_translate_to_english(self):
        localization.set_language("en")
        self.assertEqual(localization.translate("Мои станции"), "My Stations")
        self.assertEqual(localization.translate("Купить 5"), "Buy 5")
        self.assertEqual(
            localization.translate("Аванпост 2 • ВАША СТАНЦИЯ"),
            "Outpost 2 • YOUR STATION")


if __name__ == "__main__":
    unittest.main()
