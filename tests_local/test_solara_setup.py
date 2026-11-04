from dataclasses import replace
import unittest

import ipyvuetify as v
import solara

from component.solara.setup import WorkflowQuestions, MappingTable, YearSelection
from mgci.domain.configuration import Workflow
from mgci.infrastructure.defaults import initial_configuration
from test_solara_components import walk


class SetupComponentTests(unittest.TestCase):
    def test_questionnaire_changes_do_not_validate_draft_or_select_transition(self):
        config = solara.reactive(initial_configuration(2026))
        @solara.component
        def Harness():
            WorkflowQuestions(config.value.workflow, lambda value: config.set(replace(config.value, workflow=value)))
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        questions = [w for w in walk(root) if isinstance(w, v.RadioGroup)]
        questions[0].v_model = True
        self.assertEqual(config.value.workflow, Workflow.CUSTOM_CANONICAL)
        questions = [w for w in walk(root) if isinstance(w, v.RadioGroup)]
        questions[1].v_model = True
        self.assertEqual(config.value.workflow, Workflow.CUSTOM_RECLASSIFY)
        self.assertFalse(config.value.transition.explicitly_selected)

    def test_mapping_change_keeps_integer_codes_and_unassigned_is_invalid(self):
        selected = solara.reactive(initial_configuration(2026).a)
        @solara.component
        def Harness():
            MappingTable(selected.value, (10, 190), lambda value: selected.set(replace(selected.value, mapping=value)))
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        fields = [w for w in walk(root) if isinstance(w, v.Select)]
        fields[0].v_model = 4
        self.assertEqual(dict(selected.value.mapping)[10], 4)
        fields[0].v_model = None
        self.assertEqual(dict(selected.value.mapping)[10], 0)

    def test_year_clear_does_not_retain_previous_valid_year(self):
        selected = solara.reactive(initial_configuration(2026).a)
        @solara.component
        def Harness():
            YearSelection(selected.value, 'a', lambda value: selected.set(replace(selected.value, images=value)))
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        field = next(w for w in walk(root) if isinstance(w, v.TextField))
        field.v_model = ''
        self.assertEqual(selected.value.images[0].year, 0)
