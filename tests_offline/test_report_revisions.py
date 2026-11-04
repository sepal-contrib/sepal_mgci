import unittest
from dataclasses import replace

from test_domain import configuration
from mgci.application.state import SessionState
from mgci.application.reports import prepare_report


class ReportRevisionTests(unittest.TestCase):
    def setUp(self):
        self.state = SessionState(configuration())
        for key in ('a', 'b'):
            request = self.state.prepare(key, 'statistics')
            self.state.accept(request, {'area': 7})

    def test_report_revision_captures_explicit_metadata_without_changing_statistics(self):
        original = self.state.current('a', 'statistics')
        self.state.edit(replace(self.state.configuration, source='Corrected source', ref_area='020'))
        report = prepare_report(self.state, ('a',))
        self.assertEqual(report.source, 'Corrected source')
        self.assertEqual(report.ref_area, '020')
        self.assertIs(report.artifacts[0], original)
        self.assertNotEqual(original.request.configuration.source, report.source)
        self.state.edit(replace(self.state.configuration, source='Later edit'))
        self.assertEqual(report.source, 'Corrected source')

    def test_a_and_combined_and_repeat_reports_have_distinct_paths(self):
        self.state.edit(replace(self.state.configuration, aoi_label='AND'))
        reports = [prepare_report(self.state, keys, 9144, sequence)
                   for sequence, keys in enumerate((('a',), ('a', 'b'), ('a', 'b')), 1)]
        self.assertEqual([report.filename for report in reports],
                         ['SDG1542_AND9144_sub_a.xlsx', 'SDG1542_AND9144_2.xlsx', 'SDG1542_AND9144_3.xlsx'])
        self.assertEqual(reports[0].folder, 'SDG1542_AND')
        self.assertEqual(tuple(a.request.slot[0] for a in reports[1].artifacts), ('a', 'b'))

    def test_selected_missing_or_stale_output_blocks_report(self):
        self.state.edit(replace(self.state.configuration, transition=None))
        prepare_report(self.state, ('a',))
        with self.assertRaises(ValueError):
            prepare_report(self.state, ('a', 'b'))
        with self.assertRaises(ValueError):
            prepare_report(self.state, ())
