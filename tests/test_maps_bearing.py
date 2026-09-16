from __future__ import annotations

import unittest

from fieldos.maps import bearing_distance


class BearingDistanceTests(unittest.TestCase):
    def test_same_point_is_zero_distance(self) -> None:
        distance, bearing = bearing_distance(-37.8136, 144.9631, -37.8136, 144.9631)
        self.assertAlmostEqual(distance, 0.0, places=3)
        self.assertEqual(bearing, 0.0)

    def test_due_north_is_bearing_zero(self) -> None:
        distance, bearing = bearing_distance(0.0, 0.0, 1.0, 0.0)
        self.assertGreater(distance, 0)
        self.assertAlmostEqual(bearing, 0.0, places=3)

    def test_due_east_is_bearing_ninety(self) -> None:
        distance, bearing = bearing_distance(0.0, 0.0, 0.0, 1.0)
        self.assertGreater(distance, 0)
        self.assertAlmostEqual(bearing, 90.0, places=3)

    def test_due_south_is_bearing_180(self) -> None:
        _distance, bearing = bearing_distance(0.0, 0.0, -1.0, 0.0)
        self.assertAlmostEqual(bearing, 180.0, places=3)

    def test_due_west_is_bearing_270(self) -> None:
        _distance, bearing = bearing_distance(0.0, 0.0, 0.0, -1.0)
        self.assertAlmostEqual(bearing, 270.0, places=3)

    def test_one_degree_of_latitude_is_about_111km(self) -> None:
        distance, _bearing = bearing_distance(0.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(distance, 111195, delta=200)


if __name__ == "__main__":
    unittest.main()
