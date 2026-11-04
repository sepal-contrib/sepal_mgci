import asyncio
from dataclasses import replace
import unittest

import ipyvuetify as v
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.landcover import LandCoverPanel
from component.solara.mapping import MappingEditor
from component.solara.session import use_session_state
from mgci.application.state import ResourceState
from mgci.domain.configuration import Workflow
from test_report_adapter import report_state
from test_solara_calculation import until


def widgets(root):
    seen = set()
    def visit(value):
        if isinstance(value, dict):
            for child in value.values():
                yield from visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                yield from visit(child)
        elif hasattr(value, 'children') and id(value) not in seen:
            seen.add(id(value))
            yield value
            yield from visit(value.children)
            yield from visit(getattr(value, 'v_slots', ()))
    yield from visit(root)


class Interface:
    async def get_folder_async(self):
        return 'projects/test/assets'

    async def get_assets_async(self, folder):
        return []


class LandCoverParityTests(unittest.IsolatedAsyncioTestCase):
    async def test_reclassification_retains_stepper_and_table_tools(self):
        config = replace(report_state().configuration, workflow=Workflow.CUSTOM_RECLASSIFY)
        resources = {key: ResourceState() for key in ('a', 'b', 'transition')}
        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            NotificationProvider()
            LandCoverPanel(state, publish, resources, Interface(), None, None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        steps = [widget for widget in widgets(root) if isinstance(widget, v.StepperStep)]
        self.assertEqual(len(steps), 4)
        self.assertEqual([step.step for step in steps], [1, 2, 3, 4])
        selectors = [widget for widget in widgets(root) if isinstance(widget, v.Combobox)]
        self.assertEqual(len(selectors), 1)
        buttons = [widget for widget in widgets(root) if isinstance(widget, v.Btn)]
        self.assertEqual(sum('Get classes' in button.children for button in buttons), 1)
        # Inside the field's outer slot, so it centres on the input and not on the hint below.
        slot = next(item for item in selectors[0].v_slots if item['name'] == 'append-outer')
        self.assertIn('Get classes', slot['children'].children)
        tables = [widget for widget in widgets(root) if isinstance(widget, v.SimpleTable)]
        self.assertEqual(sum(table.height == '300px' for table in tables), 2)
        # Footer Close buttons; the legacy alert dialog's full-width Close is plain.
        close = [button for button in buttons if 'Close' in button.children and not button.block]
        self.assertTrue(close)
        self.assertTrue(all(button.outlined for button in close))
        await asyncio.sleep(.01)

    async def test_mapping_tools_keep_info_and_save_dialogs_and_capture_csv(self):
        config = report_state().configuration
        output = []
        class Workspace:
            async def mkdir_async(self, path, parents=False):
                pass
            async def write_async(self, path, content):
                output.append((path, content))
        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            NotificationProvider()
            MappingEditor(state, publish, 'a', Workspace(), None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        def icon_button(icon):
            return next(widget for widget in widgets(root) if isinstance(widget, v.Btn)
                        and any(isinstance(child, v.Icon) and icon in child.children for child in widget.children))
        toolbar = next(widget for widget in widgets(root) if isinstance(widget, v.Toolbar))
        icons = [child.children[0] for widget in widgets(toolbar) if isinstance(widget, v.Btn)
                 for child in widget.children if isinstance(child, v.Icon)]
        self.assertEqual(icons, ['mdi-information', 'mdi-content-save', 'mdi-upload'])
        bar = next(widget for widget in widgets(root) if isinstance(widget, v.ProgressLinear))
        self.assertIn(bar.color, ('error', 'warning', 'success'))
        icon_button('mdi-information').fire_event('click', None)
        dialog = next(widget for widget in widgets(root) if isinstance(widget, v.Dialog))
        self.assertTrue(dialog.v_model)
        self.assertIn('Land cover classes', str([w.children for w in widgets(dialog) if isinstance(w, v.CardTitle)]))
        next(widget for widget in widgets(root) if isinstance(widget, v.Btn) and 'Cancel' in widget.children).fire_event('click', None)
        icon_button('mdi-content-save').fire_event('click', None)
        field = next(widget for widget in widgets(root) if isinstance(widget, v.TextField))
        field.v_model = 'my mapping'
        next(widget for widget in widgets(root) if isinstance(widget, v.Btn) and 'Save' in widget.children).fire_event('click', None)
        await until(lambda: bool(output))
        self.assertEqual(output[0][0], 'module_results/sdg_indicators/15.4.2/custom_map_matrix/my_mapping.csv')
        self.assertTrue(output[0][1].startswith(b'from_code,to_code'))

    async def test_asset_search_and_parent_rerender_do_not_commit_or_repeat_browsing(self):
        from component.solara.asset_field import LandCoverAssetField
        import reacton.ipyvuetify as rv
        commits, calls = [], []
        trigger = solara.reactive(0)
        class Browser(Interface):
            async def get_assets_async(self, folder):
                calls.append(folder)
                return [{'id': 'lc', 'type': 'IMAGE_COLLECTION'}]
        interface = Browser()
        @solara.component
        def Harness():
            trigger.value
            LandCoverAssetField('lc', commits.append, interface)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        await until(lambda: bool(calls))
        field = next(widget for widget in widgets(root) if isinstance(widget, v.Combobox))
        field.search_input = 'projects/part'
        trigger.set(1)
        await asyncio.sleep(.02)
        self.assertEqual(commits, [])
        self.assertEqual(len(calls), 1)
        field.v_model = 'new/asset'
        self.assertEqual(commits, ['new/asset'])

    async def test_late_mapping_import_cannot_overwrite_an_edit(self):
        from unittest.mock import patch
        import reacton.ipyvuetify as rv
        config = report_state().configuration
        future = asyncio.get_running_loop().create_future()
        seen, started = [], []
        class Workspace:
            async def read_bytes_async(self, path):
                started.append(path)
                return await future
        @solara.component
        def FilePicker(value, on_value, **kwargs):
            rv.TextField(v_model=value, on_v_model=on_value)
        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            seen.append(state)
            NotificationProvider()
            MappingEditor(state, publish, 'a', Workspace(), object())
        with patch('component.solara.mapping.FileInputComponent', FilePicker):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            upload = next(widget for widget in widgets(root) if isinstance(widget, v.Btn)
                          and any(isinstance(child, v.Icon) and 'mdi-upload' in child.children for child in widget.children))
            upload.fire_event('click', None)
            next(widget for widget in widgets(root) if isinstance(widget, v.TextField)).v_model = 'mapping.csv'
            next(widget for widget in widgets(root) if isinstance(widget, v.Btn) and 'Load' in widget.children).fire_event('click', None)
            await until(lambda: bool(started))
            edited = ((10, 1), (20, 1))
            state = seen[-1]
            state.edit(replace(state.configuration, a=replace(state.configuration.a, mapping=edited)))
            future.set_result(b'from_code,to_code\n10,4\n20,1\n')
            await until(lambda: any(isinstance(widget, v.Alert) and widget.type == 'error' for widget in widgets(root)))
            self.assertEqual(state.configuration.a.mapping, edited)


class StepCardTests(unittest.IsolatedAsyncioTestCase):
    async def test_step_contents_are_flat(self):
        from mgci.application.state import ResourceState
        config = replace(report_state().configuration, workflow=Workflow.CUSTOM_RECLASSIFY)
        resources = {key: ResourceState() for key in ('a', 'b', 'transition')}
        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            NotificationProvider()
            LandCoverPanel(state, publish, resources, Interface(), None, None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        contents = [widget for widget in widgets(root) if isinstance(widget, v.StepperContent)]
        self.assertEqual(len(contents), 4)
        for content in contents:
            card = next(child for child in content.children if isinstance(child, v.Card))
            self.assertEqual(card.elevation, 0)
