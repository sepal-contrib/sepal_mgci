import asyncio
from dataclasses import replace
from io import BytesIO
import unittest
from unittest.mock import patch

import ipyvuetify as v
import pandas as pd
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.years import IndicatorYears, YearListA
from component.solara.settings import CalculationAction, ReportAction
from mgci.application.reports import prepare_report
from mgci.domain.configuration import ImageSelection, TransitionTable
from mgci.infrastructure.reports import build_report_revision
from test_report_adapter import report_state
from test_solara_components import walk
from test_solara_calculation import until


def walk_slots(widget):
    """walk() plus v_slots, where tooltip activators live."""
    yield from walk(widget)
    for item in walk(widget):
        for slot in getattr(item, 'v_slots', ()) or ():
            child = slot.get('children')
            for nested in (child if isinstance(child, (list, tuple)) else [child]):
                if nested is not None and not isinstance(nested, str):
                    yield from walk_slots(nested)


class YearDialogTests(unittest.TestCase):
    def render(self, state):
        config = solara.reactive(state.configuration)
        enabled = solara.reactive(True)
        @solara.component
        def Harness():
            IndicatorYears(config.value, 'a', enabled.value, enabled.set,
                           lambda images: config.set(replace(config.value, a=replace(config.value.a, images=images))))
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        def button(label):
            return next(w for w in walk_slots(root) if isinstance(w, v.Btn)
                        and (label in w.children or w.attributes.get('aria-label') == label))
        def editor():
            return next(w for w in walk(root) if isinstance(w, YearListA))
        def open_dialog():
            next(w for w in walk(root) if isinstance(w, v.Btn) and w.children
                 and getattr(w.children[0], 'children', None) == ['mdi-layers-plus']).fire_event('click', None)
        return config, enabled, button, editor, open_dialog

    def test_close_discards_the_draft_and_reopening_shows_the_saved_years(self):
        state = report_state()
        saved = state.configuration.a.images
        config, _, button, editor, open_dialog = self.render(state)
        open_dialog()
        editor().v_model = {1: {'asset': 'lc/2000', 'year': None}}
        button('Reset all values').fire_event('click', None)
        self.assertEqual(editor().v_model, {1: {'asset': None, 'year': None}})
        button('Close').fire_event('click', None)
        self.assertEqual(config.value.a.images, saved)
        open_dialog()
        self.assertEqual(editor().v_model, {1: {'asset': saved[0].asset, 'year': saved[0].year}})

    def test_ok_saves_the_draft_and_disable_keeps_years(self):
        state = report_state()
        config, enabled, button, editor, open_dialog = self.render(state)
        open_dialog()
        editor().v_model = {1: {'asset': 'lc/2000', 'year': 2005}}
        self.assertEqual(config.value.a.images, state.configuration.a.images)
        button('OK').fire_event('click', None)
        self.assertEqual(config.value.a.images, (ImageSelection('lc/2000', 2005),))
        enabled.set(False)
        enabled.set(True)
        self.assertEqual(config.value.a.images, (ImageSelection('lc/2000', 2005),))
        close, ok = button('Close'), button('OK')
        self.assertEqual((close.color, close.outlined, ok.color), ('primary', True, 'primary'))
        self.assertEqual(button('Reset all values').color, 'primary')


class SettingsActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_only_action_does_not_require_or_run_b(self):
        state = report_state()
        ran = []
        async def run(request):
            ran.append(request.slot[0])
            return {'2000': {'sub_a': []}}
        @solara.component
        def Harness():
            NotificationProvider()
            CalculationAction(state, lambda: None, ('a',), run)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate indicator' in w.children)
        button.fire_event('click', None)
        await until(lambda: state.current('a', 'statistics') is not None)
        self.assertEqual(ran, ['a'])
        self.assertIsNone(state.current('b', 'statistics'))

    async def test_both_action_accepts_each_selected_result(self):
        state = report_state()
        images = tuple(ImageSelection(f'lc/{year}', year) for year in (2000, 2015, 2018))
        selected = replace(state.configuration.a, images=images,
                           evidence=replace(state.configuration.a.evidence, images=tuple(image.asset for image in images)))
        state.edit(replace(state.configuration, a=selected, b=selected,
                           transition=TransitionTable(tuple((left, right, 2) for left in (1, 4) for right in (1, 4)), 'matrix.csv', 'digest', True)))
        ran = []
        async def run(request):
            ran.append(request.slot[0])
            return {'captured': request.slot[0]}
        @solara.component
        def Harness():
            NotificationProvider()
            CalculationAction(state, lambda: None, ('a', 'b'), run)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate indicator' in w.children)
        button.fire_event('click', None)
        await until(lambda: state.current('b', 'statistics') is not None)
        self.assertEqual(ran, ['a', 'b'])
        self.assertEqual(state.current('a', 'statistics').payload['captured'], 'a')

    async def test_edit_during_combined_action_rejects_late_result(self):
        state = report_state()
        future = asyncio.get_running_loop().create_future()
        submitted = []
        async def run(request):
            submitted.append(request)
            return await future
        @solara.component
        def Harness():
            NotificationProvider()
            CalculationAction(state, lambda: None, ('a',), run)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate indicator' in w.children)
        button.fire_event('click', None)
        await until(lambda: bool(submitted))
        state.edit(replace(state.configuration, aoi_identity='changed'))
        future.set_result({'area': 1})
        await until(lambda: 'Calculate indicator' in button.children)
        self.assertIsNone(state.current('a', 'statistics'))
        self.assertEqual(state.history, ())

    async def test_report_download_uses_captured_metadata_and_unique_revision(self):
        state = report_state()
        request = state.prepare('a', 'statistics')
        state.accept(request, {'2000': {'sub_a': [{'biobelt': 1, 'groups': [{'lc': 4, 'sum': 3.0}, {'lc': 1, 'sum': 1.0}]}]}})
        original = state.current('a', 'statistics')
        state.edit(replace(state.configuration, source='Corrected source'))
        revision = prepare_report(state, ('a',))
        workbook = build_report_revision(revision)
        report = pd.read_excel(BytesIO(workbook), 'Table3_ER_MTN_GRNCVI')
        self.assertEqual(set(report.SOURCE_DETAIL), {'Corrected source'})
        self.assertEqual(original.request.configuration.source, 'Original source')
        self.assertIn(75.0, report.OBS_VALUE.tolist())

    async def test_repeat_report_exports_keep_distinct_file_names(self):
        state = report_state()
        state.edit(replace(state.configuration, aoi_label='AND'))
        request = state.prepare('a', 'statistics')
        state.accept(request, {'2000': {'sub_a': [{'biobelt': 1, 'groups': [{'lc': 4, 'sum': 3.0}, {'lc': 1, 'sum': 1.0}]}]}})
        stored = {}
        class Workspace:
            async def mkdir_async(self, path, parents=False):
                pass
            async def write_async(self, path, content):
                self_check.assertNotIn(path, stored)
                stored[path] = content
        self_check = self
        saved = []
        @solara.component
        def Harness():
            NotificationProvider()
            ReportAction(state, Workspace(), indicators=('a',), on_saved=saved.append)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        def button():
            return next(w for w in walk(root) if isinstance(w, v.Btn) and 'Export reporting tables' in w.children)
        button().fire_event('click', None)
        await until(lambda: len(stored) == 1 and len(saved) == 1)
        state.edit(replace(state.configuration, source='Corrected source'))
        button().fire_event('click', None)
        await until(lambda: len(stored) == 2 and len(saved) == 2 and 'Export reporting tables' in button().children)
        first, second = stored
        self.assertRegex(first, r'^module_results/sdg_indicators/15\.4\.2/reports/SDG1542_AND/SDG1542_AND\d{4}_sub_a\.xlsx$')
        self.assertEqual(second, first.replace('_sub_a.xlsx', '_sub_a_2.xlsx'))
        self.assertEqual(set(pd.read_excel(BytesIO(stored[first]), 'Table3_ER_MTN_GRNCVI').SOURCE_DETAIL), {'Original source'})
        self.assertEqual(set(pd.read_excel(BytesIO(stored[second]), 'Table3_ER_MTN_GRNCVI').SOURCE_DETAIL), {'Corrected source'})
        self.assertEqual(saved[-1][1], 'module_results/sdg_indicators/15.4.2/reports/SDG1542_AND')
