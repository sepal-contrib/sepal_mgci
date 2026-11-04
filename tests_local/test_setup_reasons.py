import unittest
from dataclasses import replace

from mgci.domain.configuration import DatasetEvidence, Workflow
from mgci.domain.validation import NotReady, readiness
from mgci.infrastructure.defaults import initial_configuration


class LegacyReasonTests(unittest.TestCase):
    def reason(self, config, indicator='a', unreadable=False):
        from component.solara.landcover import legacy_reason
        return legacy_reason(indicator, readiness(config, indicator, 'setup').issues, config, unreadable)[0]

    def test_classes_not_read_name_the_missing_input(self):
        config = initial_configuration(2024)
        self.assertEqual(self.reason(config), 'no_aoi')
        config = replace(config, aoi_identity='aoi')
        self.assertEqual(self.reason(config), 'no_images')
        reclassify = replace(config, workflow=Workflow.CUSTOM_RECLASSIFY,
                             a=replace(config.a, asset='users/me/lc'))
        self.assertEqual(self.reason(reclassify), 'no_matrix')
        self.assertEqual(self.reason(reclassify, unreadable=True), 'no_images')

    def test_unknown_classes_are_listed(self):
        from component.solara.landcover import legacy_reason
        from component.message import cm
        config = initial_configuration(2024)
        evidence = DatasetEvidence('users/me/lc', ('users/me/lc/2000',), (1, 200), 'aoi', 'ready')
        config = replace(config, aoi_identity='aoi', workflow=Workflow.CUSTOM_CANONICAL,
                         a=replace(config.a, asset='users/me/lc', evidence=evidence, mapping=(), images=()))
        issues = readiness(config, 'a', 'setup').issues
        key, text = legacy_reason('a', issues, config)
        self.assertEqual(key, 'unknown_classes')
        self.assertIn('200', text)
        self.assertNotIn('Issue(', text)

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
