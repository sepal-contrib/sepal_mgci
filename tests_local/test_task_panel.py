import asyncio
from unittest.mock import patch
import unittest

import ipyvuetify as v
import reacton.ipyvuetify as rv
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.tasks import TaskPanel
from test_report_adapter import report_state
from test_solara_components import walk
from test_solara_calculation import until


class TaskPanelTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_transition_error_can_retry_and_new_task_requires_new_selection(self):
        state = report_state()
        reads, writes = [], []
        payload = {'2000_2015_2018': {}}
        class Workspace:
            async def read_bytes_async(self, path):
                reads.append(path)
                if path == 'unavailable.csv':
                    raise OSError('Transition file is unavailable')
                if path == 'invalid.csv':
                    return b'not,a,transition\n'
                return b'from_code,to_code,impact_code\n1,1,2\n'
            async def mkdir_async(self, *args, **kwargs):
                pass
            async def write_async(self, path, content, **kwargs):
                writes.append((path, content))
        async def retrieve(*args):
            return None, payload, {'model_state': {}}
        @solara.component
        def Picker(value, on_value=None, label='', **kwargs):
            rv.TextField(label=label, v_model=value, on_v_model=on_value)
        @solara.component
        def Harness():
            NotificationProvider()
            TaskPanel(state, lambda: None, Workspace(), object(), object(), object())
        with patch('component.solara.tasks.FileInputComponent', Picker), \
             patch('component.solara.tasks.retrieve', retrieve), \
             patch('component.solara.tasks.build_legacy_workbook', return_value=b'historical workbook') as workbook:
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            def fields():
                return [widget for widget in walk(root) if isinstance(widget, v.TextField)]
            def report_downloads():
                return [widget for widget in walk(root) if isinstance(widget, v.Btn) and 'Download report' in widget.children]
            fields()[0].v_model = 'tasks/first.json'
            button = next(widget for widget in walk(root) if isinstance(widget, v.Btn)
                          and 'Download & Export tables' in widget.children)
            button.fire_event('click', None)
            await until(lambda: len(fields()) == 2)
            self.assertEqual(fields()[1].v_model, '')
            for path in ('unavailable.csv', 'invalid.csv'):
                with self.subTest(path=path):
                    fields()[1].v_model = path
                    button.fire_event('click', None)
                    await until(lambda: path in reads and 'Download & Export tables' in button.children)
                    self.assertEqual(len(fields()), 2)
                    self.assertEqual(fields()[1].v_model, path)
                    self.assertEqual(writes, [])
                    workbook.assert_not_called()
            fields()[1].v_model = 'original.csv'
            button.fire_event('click', None)
            await until(lambda: len(writes) == 1 and bool(report_downloads()))
            self.assertEqual(writes[0][1], b'historical workbook')
            self.assertEqual(workbook.call_args.args[2].source, 'original.csv')
            self.assertEqual(state.history, ())
            self.assertIsNone(state.current('b', 'statistics'))
            fields()[0].v_model = 'tasks/second.json'
            self.assertEqual(len(fields()), 1)
            self.assertEqual(report_downloads(), [])
            button.fire_event('click', None)
            await until(lambda: len(fields()) == 2)
            self.assertEqual(fields()[1].v_model, '')
            self.assertEqual(reads, ['unavailable.csv', 'invalid.csv', 'original.csv'])
            self.assertEqual(len(writes), 1)

    async def test_retrieved_workbook_is_downloadable_and_previous_report_is_retained(self):
        state = report_state()
        request = state.prepare('a', 'statistics')
        writes = []
        class Workspace:
            async def mkdir_async(self, *args, **kwargs):
                pass
            async def write_async(self, path, content, **kwargs):
                self_test.assertFalse(kwargs.get('overwrite', False))
                self_test.assertNotIn(path, [row[0] for row in writes])
                writes.append((path, content))
        self_test = self
        async def retrieve(*args):
            return request, {}, {}
        @solara.component
        def Picker(value, on_value=None, **kwargs):
            rv.TextField(v_model=value.value if hasattr(value, 'value') else value,
                         on_v_model=value.set if hasattr(value, 'set') else on_value)
        @solara.component
        def Harness():
            NotificationProvider()
            TaskPanel(state, lambda: None, Workspace(), object(), object(), object())
        with patch('component.solara.tasks.FileInputComponent', Picker), \
             patch('component.solara.tasks.retrieve', retrieve), \
             patch('component.solara.tasks.build_workbook', return_value=b'workbook'):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            next(w for w in walk(root) if isinstance(w, v.TextField)).v_model = 'tasks/example.json'
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and any('retrieve' in str(x).lower() or 'download & export' in str(x).lower() for x in w.children))
            button.fire_event('click', None)
            await until(lambda: bool(writes))
            await asyncio.sleep(.05)
            self.assertTrue(any('Download report' in str(w.children) for w in walk(root) if isinstance(w, v.Btn)))
            button.fire_event('click', None)
            await until(lambda: len(writes) == 2)
            self.assertEqual([row[1] for row in writes], [b'workbook', b'workbook'])

    async def test_selecting_another_task_rejects_late_retrieval(self):
        state = report_state()
        request = state.prepare('a', 'statistics')
        future = asyncio.get_running_loop().create_future()
        started, writes = [], []
        class Workspace:
            async def mkdir_async(self, *args, **kwargs): pass
            async def write_async(self, *args, **kwargs): writes.append(args)
        async def retrieve(*args):
            started.append(True)
            try:
                return await asyncio.shield(future)
            except asyncio.CancelledError:
                return await future
        @solara.component
        def Picker(value, on_value=None, **kwargs):
            rv.TextField(v_model=value.value if hasattr(value, 'value') else value,
                         on_v_model=value.set if hasattr(value, 'set') else on_value)
        @solara.component
        def Harness():
            NotificationProvider()
            TaskPanel(state, lambda: None, Workspace(), object(), object(), object())
        with patch('component.solara.tasks.FileInputComponent', Picker), patch('component.solara.tasks.retrieve', retrieve), patch('component.solara.tasks.build_workbook', return_value=b'workbook'):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            field = next(w for w in walk(root) if isinstance(w, v.TextField))
            field.v_model = 'tasks/first.json'
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and any('download & export' in str(x).lower() for x in w.children))
            button.fire_event('click', None)
            await until(lambda: bool(started))
            field.v_model = 'tasks/second.json'
            future.set_result((request, {}, {}))
            await asyncio.sleep(.1)
            self.assertEqual(writes, [])
            self.assertIsNone(state.current('a', 'statistics'))


class TaskPanelLegacyLayoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_button_stays_enabled_and_explains_a_missing_file(self):
        from mgci.application.state import SessionState
        from mgci.infrastructure.defaults import initial_configuration
        state = SessionState(initial_configuration(2026))
        @solara.component
        def Picker(value, on_value=None, label='', **kwargs):
            rv.TextField(label=label, v_model=value, on_v_model=on_value)
        @solara.component
        def Harness():
            NotificationProvider()
            TaskPanel(state, lambda: None, object(), object(), object(), object())
        with patch('component.solara.tasks.FileInputComponent', Picker):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Download & Export tables' in w.children)
            self.assertFalse(button.disabled)
            button.fire_event('click', None)
            await asyncio.sleep(.05)
            alerts = [w for w in walk(root) if isinstance(w, v.Alert)]
            self.assertTrue(any('Please select a task file.' in w.children for w in alerts))
            text = ' '.join(str(c) for w in walk(root) for c in (getattr(w, 'children', ()) or ()) if isinstance(c, str))
            self.assertNotIn('Task record', text)
