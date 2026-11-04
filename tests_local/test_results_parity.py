import unittest
from dataclasses import replace

import ipyvuetify as v
import solara

from component.solara.charts import AChart, BChart
from component.widget.mgci_dashboard import MgciDashboard
from mgci.domain.configuration import ImageSelection, TransitionTable
from test_report_adapter import report_state
from test_solara_components import walk


class ChartParityTests(unittest.IsolatedAsyncioTestCase):
    async def test_changing_year_retains_selected_mountain_belt(self):
        state = report_state()
        selected = state.configuration.a
        state.edit(replace(state.configuration, a=replace(selected,
            images=(ImageSelection('lc/2000', 2000), ImageSelection('lc/2005', 2005)),
            evidence=replace(selected.evidence, images=('lc/2000', 'lc/2005')))))
        request = state.prepare('a', 'statistics')
        row = {'sub_a': [{'biobelt': 1, 'groups': [{'lc': 4, 'sum': 3.0}, {'lc': 1, 'sum': 1.0}]}]}
        state.accept(request, {'2000': row, '2005': row})
        selection = solara.reactive('2000')
        @solara.component
        def Harness():
            AChart(state.current('a', 'statistics'), selection.value)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        dashboard = next(widget for widget in walk(root) if isinstance(widget, MgciDashboard))
        dashboard.belt_buttons[1].fire_event('click', None)
        selection.set('2005')
        changed = next(widget for widget in walk(root) if isinstance(widget, MgciDashboard))
        self.assertEqual(changed.selected_belt, 1)

    async def test_b_flow_and_matrix_keep_period_and_impact_explanations(self):
        state = report_state()
        selected = state.configuration.b
        images = tuple(ImageSelection(f'lc/{year}', year) for year in (2000, 2015, 2018))
        selected = replace(selected, images=images,
            evidence=replace(selected.evidence, images=tuple(image.asset for image in images)))
        matrix = TransitionTable(((1, 1, 2), (1, 4, 3), (4, 1, 1), (4, 4, 2)), 'matrix.csv', 'digest', True)
        state.edit(replace(state.configuration, b=selected, transition=matrix))
        request = state.prepare('b', 'statistics')
        rows = [{'biobelt': 1, 'groups': [{'lc': 104, 'sum': 3.0}, {'lc': 401, 'sum': 1.0}]}]
        state.accept(request, {'2000_2015_2018': {'baseline_transition': rows, 'report_transition': rows}})
        root, context = solara.render(BChart(state.current('b', 'statistics'), 'baseline'), handle_error=False)
        self.addCleanup(context.close)
        text = lambda: ' '.join(child for w in walk(root) for child in getattr(w, 'children', ()) if isinstance(child, str))
        self.assertIn('From · 2000', text())
        self.assertIn('To · 2015', text())
        self.assertTrue(any('#515151' in str(getattr(w, 'style_', '')) for w in walk(root)))
        matrix_button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Matrix' in w.children)
        matrix_button.fire_event('click', None)
        self.assertIn('From class ↓', text())
        self.assertIn('No observed area', text())
        self.assertIn('Degradation', text())


class ChartResizeTests(unittest.IsolatedAsyncioTestCase):
    async def test_shown_dialog_nudges_each_chart_to_redraw(self):
        import asyncio
        from component.solara.charts import _charts
        state = report_state()
        selected = state.configuration.b
        images = tuple(ImageSelection(f'lc/{year}', year) for year in (2000, 2015, 2018))
        selected = replace(selected, images=images,
            evidence=replace(selected.evidence, images=tuple(image.asset for image in images)))
        matrix = TransitionTable(((1, 1, 2), (1, 4, 3), (4, 1, 1), (4, 4, 2)), 'matrix.csv', 'digest', True)
        state.edit(replace(state.configuration, b=selected, transition=matrix))
        request = state.prepare('b', 'statistics')
        rows = [{'biobelt': 1, 'groups': [{'lc': 104, 'sum': 3.0}, {'lc': 401, 'sum': 1.0}]}]
        state.accept(request, {'2000_2015_2018': {'baseline_transition': rows, 'report_transition': rows}})
        root, context = solara.render(BChart(state.current('b', 'statistics'), 'baseline', True), handle_error=False)
        self.addCleanup(context.close)
        charts = [chart for widget in walk(root) for chart in _charts(widget)]
        self.assertTrue(charts)
        await asyncio.sleep(.4)
        self.assertTrue(all({'mgci-resize-a', 'mgci-resize-b'} & set(chart._dom_classes) for chart in charts))
