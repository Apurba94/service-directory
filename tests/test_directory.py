import unittest
from datetime import date, datetime

from service_directory import core, create_app
from service_directory.core import Service, distance_km, gaps, is_open, match, parse_hours, single_points, stale

MON = datetime(2026, 11, 2, 10, 0)      # a Monday


class TestDistance(unittest.TestCase):
    def test_known_distances(self):
        self.assertAlmostEqual(distance_km(0, 0, 0, 1), 111.195, places=2)
        self.assertAlmostEqual(distance_km(23.8103, 90.4125, 21.4272, 92.0058), 310, delta=8)     # Dhaka to Cox's Bazar

    def test_symmetry_and_zero(self):
        self.assertEqual(distance_km(10, 20, 10, 20), 0)
        self.assertAlmostEqual(distance_km(1, 2, 3, 4), distance_km(3, 4, 1, 2))

    def test_across_the_date_line(self):
        self.assertAlmostEqual(distance_km(0, 179.5, 0, -179.5), 111.195, places=2)


class TestHours(unittest.TestCase):
    def test_parse(self):
        t = parse_hours("Sun-Thu 09:00-17:00; Sat 10:00-13:00")
        self.assertEqual(sorted(t), [0, 1, 2, 3, 5, 6])
        self.assertEqual(t[5], [(600, 780)])

    def test_week_wrap(self):
        self.assertEqual(set(parse_hours("Fri-Mon 09:00-10:00")), {4, 5, 6, 0})

    def test_always(self):
        self.assertTrue(is_open("24/7", MON))

    def test_open_and_closed(self):
        self.assertTrue(is_open("Mon 09:00-17:00", MON))
        self.assertFalse(is_open("Tue 09:00-17:00", MON))
        self.assertFalse(is_open("Mon 11:00-17:00", MON))

    def test_closing_minute_is_closed(self):
        self.assertFalse(is_open("Mon 09:00-10:00", MON))

    def test_past_midnight(self):
        self.assertTrue(is_open("Sun 22:00-11:00", MON))
        self.assertFalse(is_open("Sun 22:00-09:00", MON))
        self.assertTrue(is_open("Mon 22:00-06:00", datetime(2026, 11, 2, 23, 0)))

    def test_bad_text(self):
        for bad in ("whenever", "Mon 9-5", "Xyz 09:00-10:00"):
            with self.assertRaises(ValueError):
                parse_hours(bad)


S = [Service(1, "Near clinic", ("health",), "A", 21.0, 92.0, ("bn",), "Mon-Fri 09:00-17:00"),
     Service(2, "Far clinic", ("health",), "B", 21.5, 92.0, ("rhg",), "Mon-Fri 09:00-17:00"),
     Service(3, "Women's centre", ("health", "legal"), "A", 21.0, 92.0, ("bn",), "Mon-Fri 09:00-17:00", groups=("women",)),
     Service(4, "Paid lawyer", ("legal",), "A", free=False),
     Service(5, "Night clinic", ("health",), "A", 21.0, 92.0, ("bn",), "Mon-Fri 20:00-23:00")]


class TestMatch(unittest.TestCase):
    def names(self, *a, **k):
        return [x[1].name for x in match(S, *a, **k)]

    def test_need_filters(self):
        self.assertEqual(set(self.names("legal")), {"Women's centre", "Paid lawyer"})

    def test_free_only(self):
        self.assertEqual(self.names("legal", free_only=True), ["Women's centre"])

    def test_group_only_services_are_kept_from_others(self):
        self.assertNotIn("Women's centre", self.names("health", group="men"))
        self.assertEqual(self.names("health", group="women", lat=21.0, lon=92.0)[0], "Women's centre")

    def test_nearer_wins(self):
        self.assertEqual(self.names("health", lat=21.0, lon=92.0, when=MON)[0], "Near clinic")

    def test_language_can_outweigh_distance(self):
        self.assertEqual(self.names("health", lat=21.1, lon=92.0, language="rhg")[0], "Far clinic")

    def test_open_ranks_above_closed(self):
        hits = self.names("health", lat=21.0, lon=92.0, when=MON)
        self.assertLess(hits.index("Near clinic"), hits.index("Night clinic"))

    def test_reasons_are_given(self):
        why = match(S, "health", lat=21.0, lon=92.0, when=MON, language="rhg")[0][3]
        self.assertTrue(any("km away" in w for w in why))

    def test_nothing_found(self):
        self.assertEqual(self.names("water"), [])


class TestCoordination(unittest.TestCase):
    def test_gaps(self):
        self.assertEqual(gaps(S, ["legal"], ["A", "B"]), [("legal", "B")])

    def test_single_provider(self):
        self.assertEqual(single_points(S + [Service(9, "X", ("food",))], ["food", "health", "water"]), [("food", "X")])

    def test_stale(self):
        s = [Service(1, "a", (), verified="2026-10-20"), Service(2, "b", (), verified="2026-01-01"), Service(3, "c", ())]
        r = stale(s, date(2026, 11, 2))
        self.assertEqual([x[0].name for x in r], ["b", "c"])
        self.assertIsNone(r[1][1])


class TestApp(unittest.TestCase):
    def setUp(self):
        self.a = create_app(":memory:", lambda: MON)

    def add(self, **kw):
        base = dict(name="Clinic", needs="health", area="A", languages="bn", hours="Mon-Fri 09:00-17:00", contact="Desk 3")
        return self.a.post("/add", **{**base, **kw})

    def test_flow(self):
        self.assertEqual(self.add().status, 303)
        page = self.a.get("/?need=health&area=A&language=bn").body.decode()
        self.assertIn("Clinic", page)
        self.assertIn("open now", page)
        self.assertIn("Desk 3", page)

    def test_no_match_points_to_gaps(self):
        self.add()
        self.assertIn("Check the Gaps page", self.a.get("/?need=water").body.decode())

    def test_gaps_page(self):
        self.add()
        page = self.a.get("/gaps").body.decode()
        self.assertIn("legal", page)
        self.assertIn("All details are recent", page)

    def test_bad_inputs(self):
        self.assertEqual(self.add(hours="whenever").status, 400)
        self.assertEqual(self.add(needs=" , ").status, 400)
        self.assertEqual(self.add(lat=200).status, 400)
        self.add()
        self.assertEqual(self.add().status, 409)


if __name__ == "__main__":
    unittest.main()
