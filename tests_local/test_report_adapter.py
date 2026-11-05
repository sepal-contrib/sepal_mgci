import os
import unittest
from dataclasses import replace
from io import BytesIO
from unittest.mock import patch

os.environ['DEPLOY_ENV'] = 'sepal_solara'
import pandas as pd

from mgci.application.state import SessionState
from mgci.domain.configuration import Configuration, DatasetEvidence, ImageSelection, IndicatorConfig, Workflow
from mgci.infrastructure.reports import build_workbook


def report_state():
    evidence = DatasetEvidence('lc', ('lc/2000',), (10, 20), 'aoi', 'ready')
    indicator = IndicatorConfig('lc', evidence, ((10, 4), (20, 1)), (1, 4), (ImageSelection('lc/2000', 2000),))
    return SessionState(Configuration('aoi', Workflow.CUSTOM_RECLASSIFY, indicator, indicator,
                                      aoi_name='Original AOI', ref_area='123', source='Original source'))


class ReportAdapterTests(unittest.TestCase):
    def test_workbook_uses_artifact_metadata_and_preserves_sheet_format(self):
        state = report_state()
        request = state.prepare('a', 'statistics')
        result = {'2000': {'sub_a': [{'biobelt': 1, 'groups': [{'lc': 4, 'sum': 3.0}, {'lc': 1, 'sum': 1.0}]}]}}
        state.accept(request, result)
        artifact = state.current('a', 'statistics')
        state.edit(replace(state.configuration, source='Changed source', aoi_name='Changed AOI'))
        with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
            content = build_workbook((artifact,))
        workbook = pd.ExcelFile(BytesIO(content))
        self.assertEqual(workbook.sheet_names, ['Table1_ER_MTN_TOTL', 'Table2_ER_MTN_GRNCOV', 'Table3_ER_MTN_GRNCVI'])
        report = pd.read_excel(workbook, 'Table3_ER_MTN_GRNCVI')
        self.assertEqual(set(report.SOURCE_DETAIL), {'Original source'})
        self.assertEqual(set(report.GeoAreaName), {'Original AOI'})
        self.assertIn(75.0, report.OBS_VALUE.tolist())

    def test_historical_a_report_retains_saved_metadata(self):
        from mgci.infrastructure.reports import build_historical_workbook
        payload = {'2000': {'sub_a': [{'biobelt': 1, 'groups': [{'lc': 4, 'sum': 3.0}, {'lc': 1, 'sum': 1.0}]}]}}
        metadata = {'reporting_years_sub_a': {'2000': [{'asset': 'lc/2000', 'year': 2000}]},
                    'sub_b_year': {}, 'geo_area_name': 'Historical AOI', 'ref_area': '123',
                    'source_detail': 'Historical source', 'session_id': 1234}
        content = build_historical_workbook(payload, metadata)
        report = pd.read_excel(BytesIO(content), 'Table3_ER_MTN_GRNCVI')
        self.assertEqual(set(report.GeoAreaName), {'Historical AOI'})
        self.assertIn(75.0, report.OBS_VALUE.tolist())

    def test_historical_b_report_requires_original_transition_contents(self):
        from mgci.infrastructure.reports import build_historical_workbook
        with self.assertRaises(ValueError):
            build_historical_workbook({'2000_2015_2018': {}}, {})

    def test_rejects_duplicate_indicator_artifacts(self):
        state = report_state()
        request = state.prepare('a', 'statistics')
        state.accept(request, {})
        artifact = state.current('a', 'statistics')
        with self.assertRaises(ValueError):
            build_workbook((artifact, artifact))
