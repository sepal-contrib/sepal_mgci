import unittest
from dataclasses import replace

import ipyvuetify as v
import solara

from mgci.domain.configuration import Configuration, IndicatorConfig, ScalePolicy, Workflow
from component.solara.scale import ScaleField
from component.solara.session import use_session_state
from component.message import messages


def walk(widget):
    yield widget
    for child in getattr(widget, 'children', ()) or ():
        if not isinstance(child, str):
            yield from walk(child)


class ScaleComponentTests(unittest.TestCase):
    def test_empty_custom_blocks_execution_and_native_button_restores_policy(self):
        policy = solara.reactive(ScalePolicy())
        @solara.component
        def Harness():
            ScaleField(policy.value, policy.set)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        field = next(w for w in walk(root) if isinstance(w, v.TextField))
        field.v_model = '300'
        self.assertEqual(policy.value, ScalePolicy('custom', 300))
        field.v_model = ''
        self.assertEqual(policy.value, ScalePolicy('custom', None))
        self.assertTrue(field.error_messages)
        toggle = next(w for w in walk(root) if isinstance(w, v.BtnToggle))
        toggle.v_model = 0
        self.assertEqual(policy.value, ScalePolicy())
        self.assertFalse(field.error_messages)

    def test_invalid_custom_does_not_keep_previous_valid_scale(self):
        policy = solara.reactive(ScalePolicy())
        @solara.component
        def Harness():
            ScaleField(policy.value, policy.set)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        field = next(w for w in walk(root) if isinstance(w, v.TextField))
        field.v_model = '300'
        field.v_model = '2000'
        self.assertEqual(policy.value, ScalePolicy('custom', 2000))
        self.assertTrue(field.error_messages)
        self.assertFalse(field.hide_details)

    def test_scale_field_follows_external_configuration_changes(self):
        policy = solara.reactive(ScalePolicy('custom', 300))
        @solara.component
        def Harness():
            ScaleField(policy.value, policy.set)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        field = next(w for w in walk(root) if isinstance(w, v.TextField))
        policy.set(ScalePolicy('custom', 1000))
        self.assertEqual(field.v_model, '1000')
        policy.set(ScalePolicy())
        self.assertEqual(field.v_model, '')

    def test_message_catalogue_is_valid(self):
        self.assertEqual(messages.check(), ())


class SessionHookTests(unittest.TestCase):
    def test_rerender_preserves_session_and_unmount_disposes_it(self):
        config = Configuration('', Workflow.DEFAULT, IndicatorConfig(''), IndicatorConfig(''))
        trigger = solara.reactive(0)
        seen = []
        @solara.component
        def Harness():
            trigger.value
            state, publish = use_session_state(config)
            seen.append(state)
            solara.Text(state.configuration.source)
        root, context = solara.render(Harness(), handle_error=False)
        first = seen[-1]
        first.edit(replace(config, source='Retained'))
        trigger.set(1)
        self.assertIs(seen[-1], first)
        self.assertEqual(seen[-1].configuration.source, 'Retained')
        context.close()
        with self.assertRaises(ValueError):
            first.edit(config)

    def test_separate_mounts_do_not_share_editable_state(self):
        config = Configuration('', Workflow.DEFAULT, IndicatorConfig(''), IndicatorConfig(''))
        seen = []
        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            seen.append(state)
        _, first = solara.render(Harness(), handle_error=False)
        _, second = solara.render(Harness(), handle_error=False)
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.assertIsNot(seen[0], seen[1])
        seen[0].edit(replace(config, source='Other'))
        self.assertEqual(seen[1].configuration.source, config.source)

    def test_nested_consumers_follow_publication_with_identical_state_props(self):
        config = Configuration('', Workflow.DEFAULT, IndicatorConfig(''), IndicatorConfig(''))
        owners = []
        @solara.component
        def Child(state):
            solara.Button('Get classes', disabled=not state.configuration.aoi_identity)
        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            owners.append((state, publish))
            Child(state)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        state, publish = owners[-1]
        button = next(w for w in walk(root) if isinstance(w, v.Btn))
        self.assertTrue(button.disabled)
        state.edit(replace(config, aoi_identity='selected'))
        publish()
        self.assertFalse(button.disabled)
        state.edit(config)
        publish()
        self.assertTrue(button.disabled)
        self.assertIs(owners[-1][0], state)


class YearAndScaleLookTests(unittest.TestCase):
    def test_selected_scale_button_has_white_text(self):
        @solara.component
        def Harness():
            ScaleField(ScalePolicy(), lambda value: None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        native = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Native' in w.children)
        other = next(w for w in walk(root) if isinstance(w, v.Btn) and '100' in w.children)
        self.assertIn('white--text', native.class_)
        self.assertNotIn('white--text', other.class_)

    def test_a_year_chips_are_comma_separated(self):
        from component.solara.years import IndicatorYears
        from mgci.infrastructure.defaults import initial_configuration
        from dataclasses import replace
        from mgci.domain.configuration import ImageSelection
        config = initial_configuration(2026)
        config = replace(config, a=replace(config.a, images=(ImageSelection('lc/2000', 2000), ImageSelection('lc/2015', 2015))))
        @solara.component
        def Harness():
            IndicatorYears(config, 'a', True, lambda value: None, lambda images: None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        chips = [w for w in walk(root) if isinstance(w, v.Chip)]
        self.assertGreater(len(chips), 1)
        separators = [w for w in walk(root) if isinstance(w, v.Html) and w.children == [', ']]
        self.assertEqual(len(separators), len(chips) - 1)
