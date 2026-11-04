import unittest
from dataclasses import replace

from test_domain import configuration
from mgci.domain.configuration import ImageSelection
from mgci.domain.reporting import reporting_breakpoints
from mgci.domain.provenance import scientific_identity


class ReportingTests(unittest.TestCase):
    def test_interpolation_uses_nearest_sources_and_only_bracketed_years(self):
        images = (ImageSelection('lc/2000', 2000), ImageSelection('lc/2015', 2015))
        self.assertEqual(reporting_breakpoints(images, (1995, 2000, 2005, 2010, 2015, 2018)),
                         ((2000, (images[0],)), (2005, images), (2010, images), (2015, (images[1],))))

    def test_duplicate_source_years_are_ambiguous(self):
        with self.assertRaises(ValueError):
            reporting_breakpoints((ImageSelection('first', 2000), ImageSelection('second', 2000)), (2000,))

    def test_reporting_schedule_is_part_of_a_statistics_provenance(self):
        config = configuration()
        changed = replace(config, reporting_intervals=(2000, 2015))
        self.assertNotEqual(scientific_identity(config, 'a', 'statistics'),
                            scientific_identity(changed, 'a', 'statistics'))
        self.assertEqual(scientific_identity(config, 'a', 'layer'),
                         scientific_identity(changed, 'a', 'layer'))


class ReportingReadinessTests(unittest.TestCase):
    def test_a_without_a_reportable_year_is_not_ready_for_statistics(self):
        from mgci.domain.validation import readiness
        config = configuration()
        image = ImageSelection('lc/2000', 2001)
        candidate = replace(config, a=replace(config.a, images=(image,)))
        self.assertFalse(readiness(candidate, 'a', 'statistics').ready)
        self.assertTrue(readiness(candidate, 'a', 'layer').ready)

    def test_malformed_b_year_reports_an_issue_instead_of_comparing_types(self):
        from mgci.domain.validation import readiness
        config = configuration()
        images = (replace(config.b.images[0], year='invalid'), *config.b.images[1:])
        self.assertFalse(readiness(replace(config, b=replace(config.b, images=images)), 'b', 'statistics').ready)
