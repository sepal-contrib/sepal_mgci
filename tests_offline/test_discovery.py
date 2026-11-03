import asyncio
from dataclasses import replace
import unittest

from mgci.application.state import ResourceState, SessionState
from mgci.application.discovery import select_asset, inspect_dataset
from mgci.domain.configuration import DatasetDiscovery
from test_domain import configuration


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_asset_clears_images_and_old_evidence_immediately(self):
        state = SessionState(configuration())
        before = state.configuration.b
        select_asset(state, 'a', 'new')
        self.assertIsNone(state.configuration.a.evidence)
        self.assertEqual(state.configuration.a.images, ())
        self.assertEqual(state.configuration.b, before)

    async def test_asset_away_and_back_rejects_old_success(self):
        state, resource = SessionState(configuration()), ResourceState()
        captured = state.configuration.a
        future = asyncio.get_running_loop().create_future()
        async def load(config, indicator):
            return await future
        pending = asyncio.create_task(inspect_dataset(state, resource, load, 'a'))
        await asyncio.sleep(0)
        select_asset(state, 'a', 'other')
        select_asset(state, 'a', captured.asset)
        future.set_result(DatasetDiscovery(captured.evidence, captured.images))
        self.assertFalse(await pending)
        self.assertIsNone(state.configuration.a.evidence)

    async def test_obsolete_failure_does_not_erase_new_discovery(self):
        state, resource = SessionState(configuration()), ResourceState()
        captured = state.configuration.a
        future = asyncio.get_running_loop().create_future()
        async def old(config, indicator):
            return await future
        pending = asyncio.create_task(inspect_dataset(state, resource, old, 'a'))
        await asyncio.sleep(0)
        async def new(config, indicator):
            return DatasetDiscovery(captured.evidence, captured.images)
        self.assertTrue(await inspect_dataset(state, resource, new, 'a'))
        future.set_exception(ValueError('old failure'))
        self.assertFalse(await pending)
        self.assertEqual(resource.status, 'ready')
        self.assertEqual(state.configuration.a.evidence, captured.evidence)

    async def test_empty_or_wrong_scope_discovery_does_not_enable_calculation(self):
        state, resource = SessionState(configuration()), ResourceState()
        captured = state.configuration.a
        async def wrong(config, indicator):
            return DatasetDiscovery(replace(captured.evidence, asset='other'), captured.images)
        self.assertFalse(await inspect_dataset(state, resource, wrong, 'a'))
        self.assertIsNone(state.configuration.a.evidence)
        self.assertEqual(resource.status, 'error')

    async def test_discovery_retains_only_years_still_present_in_snapshot(self):
        state, resource = SessionState(configuration()), ResourceState()
        captured = state.configuration.a
        async def load(config, indicator):
            return DatasetDiscovery(captured.evidence, captured.images)
        self.assertTrue(await inspect_dataset(state, resource, load, 'a'))
        self.assertEqual(state.configuration.a.images, captured.images)
