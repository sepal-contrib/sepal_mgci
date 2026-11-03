import asyncio
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import ipyvuetify as v
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.aoi import ReportingAreaPicker
from mgci.infrastructure.areas import reporting_admin_items
from test_solara_components import walk
from test_solara_calculation import until


class ReportingAreaTests(unittest.IsolatedAsyncioTestCase):
    async def test_changed_selection_rejects_late_success(self):
        publications = []
        future = asyncio.get_running_loop().create_future()
        started = []
        async def process(*args, **kwargs):
            started.append(True)
            try:
                return await asyncio.shield(future)
            except asyncio.CancelledError:
                return await future
        class Map:
            def remove_layer(self, *args, **kwargs):
                pass
            def add_layer(self, *args, **kwargs):
                raise AssertionError('Obsolete AOI must not reach the map')
        @solara.component
        def Harness():
            NotificationProvider()
            ReportingAreaPicker(publications.append, Map(), object())
        async def preview(*args):
            return None, 'url', (0, 0, 1, 1)
        with patch('component.solara.aoi.reporting_admin_items', return_value=[{'text':'Andorra', 'value':'285'}]), \
             patch('component.solara.aoi.process_admin', process), \
             patch('component.solara.aoi.prepare_area_preview', preview), \
             patch('component.solara.aoi.area_metadata', return_value=('Andorra', '020')):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            method = next(w for w in walk(root) if isinstance(w, v.Select))
            method.v_model = 'ADMIN0'
            await asyncio.sleep(.05)
            country = [w for w in walk(root) if isinstance(w, v.Select)][1]
            country.v_model = '285'
            await asyncio.sleep(.05)
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Select Area of Interest (AOI)' in w.children)
            self.assertFalse(button.disabled)
            button.fire_event('click', None)
            await until(lambda: bool(started))
            country.v_model = None
            future.set_result(SimpleNamespace(name='AND', method='ADMIN0'))
            await asyncio.sleep(.1)
            self.assertTrue(publications)
            self.assertTrue(all(item is None for item in publications))

    def test_country_list_matches_reference_reporting_scope(self):
        import csv
        from importlib.resources import files
        import pandas as pd
        from mgci.infrastructure.defaults import PARAMETERS
        with (PARAMETERS / 'm49_countries.csv').open() as stream:
            iso = {row['iso31661'] for row in csv.DictReader(stream, delimiter=';')}
        frame = pd.read_parquet(files('pygaul').joinpath('data/gaul_database.parquet'))
        expected = set(frame.loc[frame.iso3_code.isin(iso), 'gaul0_code'].astype(str))
        self.assertEqual({item['value'] for item in reporting_admin_items()}, expected)
