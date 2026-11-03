from dataclasses import replace
import unittest

from mgci.application.state import SessionState
from mgci.infrastructure.task_records import encode_request, decode_request, parse_task_csv
from test_domain import configuration


class TaskRecordTests(unittest.TestCase):
    def test_request_round_trip_preserves_captured_transition_and_metadata(self):
        request = SessionState(configuration()).prepare('b', 'statistics')
        self.assertEqual(decode_request(encode_request(request)), request)

    def test_changed_scientific_snapshot_is_rejected(self):
        record = encode_request(SessionState(configuration()).prepare('a', 'statistics'))
        record['configuration']['aoi_identity'] = 'other'
        with self.assertRaises(ValueError):
            decode_request(record)

    def test_background_csv_supports_ee_map_notation_without_executing_input(self):
        content = b'process_id,sub_a\n2000,"[{biobelt=1, groups=[{lc=4, sum=3.5E-4}]}]"\n'
        result = parse_task_csv(content)
        self.assertEqual(result['2000']['sub_a'][0]['groups'][0]['sum'], 3.5e-4)
        with self.assertRaises(ValueError):
            parse_task_csv(b'process_id,sub_a\n2000,__import__("os").getcwd()\n')

    def test_partial_task_result_cannot_match_complete_request(self):
        from mgci.infrastructure.task_records import validate_results
        request = SessionState(configuration()).prepare('a', 'statistics')
        with self.assertRaises(ValueError):
            validate_results(request, {'2000': {'sub_a': []}})
        validate_results(request, {str(year): {'sub_a': []} for year in (2000, 2015, 2018)})

    def test_late_background_completion_is_history_only(self):
        state = SessionState(configuration())
        request = state.prepare('a', 'statistics')
        state.edit(replace(state.configuration, aoi_identity='other'))
        artifact = state.complete_background(request, {'area': 4})
        self.assertIsNone(state.current('a', 'statistics'))
        self.assertEqual(state.history, (artifact,))
        self.assertEqual(artifact.request.configuration.aoi_identity, 'aoi')
        self.assertIs(state.complete_background(request, {'area': 4}), artifact)
