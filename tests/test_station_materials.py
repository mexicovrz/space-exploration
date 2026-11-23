import unittest

from ship import ShipSystems


class StationMaterialCargoTests(unittest.TestCase):
    def test_materials_are_weighted_and_persisted(self):
        systems = ShipSystems()
        self.assertTrue(systems.add_construction_material("scrap_metal", 5))
        self.assertAlmostEqual(systems.construction_material_weight(), 1.0)
        self.assertAlmostEqual(systems.total_weight(), 1.0)

        restored = ShipSystems()
        restored.apply_dict(systems.to_dict(), lambda _from, _to: (None, None))
        self.assertEqual(restored.construction_materials, {"scrap_metal": 5})
        self.assertAlmostEqual(restored.construction_material_weight(), 1.0)


if __name__ == "__main__":
    unittest.main()
