import unittest
from dataclasses import replace

from test_domain import configuration
from mgci.application.state import SessionState, ResourceState


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration()
        self.state = SessionState(self.config)

    def test_relevant_edit_clears_artifacts_and_rejects_late_result(self):
        ticket = self.state.prepare('a', 'statistics')
        self.assertTrue(self.state.accept(ticket, {'area': [1, 2]}))
        changed = replace(self.config, a=replace(self.config.a, mapping=((10, 2), (20, 1))))
        self.state.edit(changed)
        self.assertIsNone(self.state.current('a', 'statistics'))
        self.assertFalse(self.state.accept(ticket, {'area': [99]}))
        with self.assertRaises(ValueError):
            self.state.export_artifact(ticket)

    def test_unrelated_b_edit_does_not_reject_a(self):
        ticket = self.state.prepare('a', 'statistics')
        self.state.edit(replace(self.config, transition=None))
        self.assertTrue(self.state.accept(ticket, {'area': 7}))
        self.assertEqual(self.state.current('a', 'statistics').payload['area'], 7)

    def test_away_and_back_does_not_revive_old_task(self):
        ticket = self.state.prepare('a', 'statistics')
        self.state.edit(replace(self.config, aoi_identity='elsewhere'))
        self.state.edit(self.config)
        self.assertFalse(self.state.accept(ticket, {}))
        self.assertFalse(self.state.fail(ticket, 'old error'))

    def test_newer_request_wins_and_old_error_cannot_clear_it(self):
        old = self.state.prepare('a', 'statistics')
        new = self.state.prepare('a', 'statistics')
        self.assertTrue(self.state.accept(new, {'answer': 2}))
        self.assertFalse(self.state.accept(old, {'answer': 1}))
        self.assertFalse(self.state.fail(old, 'old failure'))
        self.assertEqual(self.state.current('a', 'statistics').payload['answer'], 2)

    def test_cancelled_request_cannot_publish_after_retry(self):
        ticket = self.state.prepare('a', 'statistics')
        self.assertTrue(self.state.cancel(ticket))
        self.assertFalse(self.state.accept(ticket, {}))
        retry = self.state.prepare('a', 'statistics')
        self.assertTrue(self.state.accept(retry, {}))

    def test_unmount_and_cross_session_results_are_rejected(self):
        ticket = self.state.prepare('a', 'statistics')
        other = SessionState(self.config)
        other.prepare('a', 'statistics')
        self.assertFalse(other.accept(ticket, {}))
        self.state.close()
        self.assertFalse(self.state.accept(ticket, {}))
        with self.assertRaises(ValueError):
            self.state.prepare('a', 'statistics')

    def test_export_uses_captured_metadata_and_immutable_payload(self):
        ticket = self.state.prepare('a', 'statistics')
        payload = {'values': [1, 2]}
        self.state.accept(ticket, payload)
        payload['values'].append(99)
        self.state.edit(replace(self.config, source='new source'))
        artifact = self.state.export_artifact(ticket)
        self.assertEqual(artifact.request.configuration.source, self.config.source)
        self.assertEqual(artifact.payload['values'], (1, 2))
        with self.assertRaises(TypeError):
            artifact.payload['new'] = 1

    def test_stale_completed_artifact_stays_in_history(self):
        ticket = self.state.prepare('a', 'statistics')
        self.state.accept(ticket, {'area': 1})
        self.state.edit(replace(self.config, aoi_identity='changed'))
        self.assertEqual(self.state.history[0].request, ticket)
        self.assertIsNone(self.state.current('a', 'statistics'))

    def test_area_edit_keeps_categorical_layer_but_clears_statistics(self):
        layer = self.state.prepare('a', 'layer', '2000')
        stats = self.state.prepare('a', 'statistics')
        self.state.accept(layer, {'url': 'tiles'})
        self.state.accept(stats, {'area': 1})
        self.state.edit(replace(self.config, rsa=True))
        self.assertIsNotNone(self.state.current('a', 'layer', '2000'))
        self.assertIsNone(self.state.current('a', 'statistics'))

    def test_invalid_setup_cannot_create_a_request(self):
        self.state.edit(replace(self.config, transition=None))
        with self.assertRaises(ValueError):
            self.state.prepare('b', 'statistics')
        self.state.prepare('a', 'statistics')

    def test_accepted_ticket_cannot_publish_twice(self):
        ticket = self.state.prepare('a', 'statistics')
        self.assertTrue(self.state.accept(ticket, {'first': True}))
        self.assertFalse(self.state.accept(ticket, {'first': False}))
        self.assertEqual(len(self.state.history), 1)


class ResourceTests(unittest.TestCase):
    def test_selection_clears_old_evidence_and_old_errors_are_ignored(self):
        state = ResourceState()
        first = state.begin('first.csv')
        self.assertTrue(state.succeed(first, 'first data'))
        second = state.begin('second.csv')
        self.assertEqual(state.status, 'loading')
        self.assertIsNone(state.value)
        self.assertFalse(state.fail(first, 'late failure'))
        self.assertTrue(state.succeed(second, 'second data'))
        self.assertEqual(state.value, 'second data')

    def test_away_and_back_and_clear_reject_old_results(self):
        state = ResourceState()
        first = state.begin('a')
        state.begin('b')
        newest = state.begin('a')
        self.assertFalse(state.succeed(first, 'obsolete'))
        state.begin('')
        self.assertFalse(state.succeed(newest, 'also obsolete'))
        self.assertEqual(state.status, 'empty')

    def test_resource_tokens_are_not_interchangeable(self):
        first, second = ResourceState(), ResourceState()
        token = first.begin('a')
        second.begin('a')
        self.assertFalse(second.succeed(token, 'wrong owner'))


class WorkflowLifecycleTests(unittest.TestCase):
    def test_reentering_custom_reclassification_requires_new_file_selection(self):
        from mgci.domain.configuration import Workflow
        config = configuration()
        state = SessionState(config)
        state.edit(replace(config, workflow=Workflow.DEFAULT))
        state.edit(config)
        with self.assertRaises(ValueError):
            state.prepare('b', 'statistics')
        state.prepare('a', 'statistics')
        state.edit(replace(state.configuration, transition=config.transition))
        state.prepare('b', 'statistics')
