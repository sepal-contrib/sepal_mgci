import unittest

from mgci.infrastructure.defaults import initial_configuration


class LegacyDefaultTests(unittest.TestCase):
    def test_initial_years_match_legacy_year_editors(self):
        config = initial_configuration(2026)
        self.assertEqual(tuple(image.year for image in config.a.images), (2000,))
        self.assertEqual(tuple(image.year for image in config.b.images), (2000, 2015, 2018))


if __name__ == '__main__':
    unittest.main()
