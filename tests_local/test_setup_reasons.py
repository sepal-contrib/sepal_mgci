import unittest
from dataclasses import replace

from mgci.domain.configuration import DatasetEvidence, Workflow
from mgci.domain.validation import NotReady, readiness
from mgci.infrastructure.defaults import initial_configuration


class SetupReasonTests(unittest.TestCase):
    def test_setup_reasons_name_the_sub_indicator_and_the_missing_input(self):
        from component.solara.setup import readiness_text
        config = initial_configuration(2024)
        self.assertEqual(readiness_text(config, 'a', 'setup'),
                         'Sub-indicator A is not ready: Get classes for the selected dataset and area.')
        evidence = DatasetEvidence('users/me/lc', ('users/me/lc/2000',), (1, 200), 'aoi', 'ready')
        canonical = replace(config, aoi_identity='aoi', workflow=Workflow.CUSTOM_CANONICAL,
                            a=replace(config.a, asset='users/me/lc', evidence=evidence, mapping=(), images=()))
        self.assertIn('outside the selected classification', readiness_text(canonical, 'a', 'setup'))

    def test_not_ready_error_is_shown_with_catalogue_text(self):
        from component.solara.setup import error_text
        config = initial_configuration(2024)
        text = error_text(NotReady(readiness(config, 'a', 'statistics').issues))
        self.assertNotIn('Issue(', text)
        self.assertIn('area of interest', text)


class ReadinessAlertTests(unittest.TestCase):
    def test_both_sub_indicators_share_one_filled_alert(self):
        import ipyvuetify as v
        import solara
        from component.solara.setup import ReadinessMessages
        from test_solara_components import walk
        root, context = solara.render(ReadinessMessages(initial_configuration(2024), ('a', 'b')), handle_error=False)
        self.addCleanup(context.close)
        alerts = [w for w in walk(root) if isinstance(w, v.Alert)]
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0].text)
        self.assertFalse(alerts[0].outlined)
        lines = [child.children[0] for child in alerts[0].children]
        self.assertEqual([line.split(' is not ready')[0] for line in lines], ['Sub-indicator A', 'Sub-indicator B'])
