import asyncio
from dataclasses import replace
import unittest

from mgci.application.landcover import WorkflowDrafts, inspect_shared_dataset, select_shared_asset
from mgci.application.state import SessionState, ResourceState
from mgci.domain.configuration import DatasetDiscovery, Workflow
from mgci.infrastructure.mappings import parse_mapping, mapping_csv
from test_domain import configuration


class MappingFilesTests(unittest.TestCase):
    def test_roundtrip_and_reject_unknown_targets_or_duplicate_codes(self):
        selected = configuration().a
        self.assertEqual(parse_mapping(mapping_csv(selected.mapping), selected), selected.mapping)
        for body in (b'from_code,to_code\n10,1\n20,9\n', b'from_code,to_code\n10,1\n10.0,2\n20,2\n'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse_mapping(body, selected)

    def test_import_applies_known_rows_like_the_legacy_loader(self):
        selected = replace(configuration().a, mapping=((10, 1), (20, 2)))
        # Extra source classes are ignored, omitted ones keep their target, 0 unassigns.
        body = b'from_code,to_code\n10,2\n30,1\n'
        self.assertEqual(parse_mapping(body, selected), ((10, 2), (20, 2)))
        self.assertEqual(parse_mapping(b'from_code,to_code\n20,0\n', selected), ((10, 1), (20, 0)))


class WorkflowTests(unittest.TestCase):
    def test_inactive_mapping_draft_survives_and_explicit_file_is_not_fallback(self):
        custom = configuration()
        defaults = replace(custom, workflow=Workflow.DEFAULT, a=replace(custom.a, mapping=((10, 2), (20, 1))))
        drafts = WorkflowDrafts(defaults)
        state = SessionState(custom)
        drafts.select(state, Workflow.DEFAULT)
        drafts.select(state, Workflow.CUSTOM_RECLASSIFY)
        self.assertEqual(state.configuration.a.mapping, custom.a.mapping)
        self.assertIsNone(state.configuration.transition)


class SharedDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_discovery_populates_both_without_copying_a_mapping_to_b(self):
        config = configuration()
        state = SessionState(replace(config, b=replace(config.b, mapping=((10, 2), (20, 1)))))
        resources = {key: ResourceState() for key in ('a', 'b')}
        calls = []
        async def load(snapshot, indicator):
            calls.append(indicator)
            return DatasetDiscovery(config.a.evidence, config.a.images)
        self.assertTrue(await inspect_shared_dataset(state, resources, load))
        self.assertEqual(calls, ['a'])
        self.assertEqual(state.configuration.a.evidence, state.configuration.b.evidence)
        self.assertEqual(state.configuration.b.mapping, ((10, 2), (20, 1)))

    async def test_away_back_edit_rejects_late_shared_result(self):
        config = configuration()
        state = SessionState(config)
        resources = {key: ResourceState() for key in ('a', 'b')}
        future = asyncio.get_running_loop().create_future()
        async def load(snapshot, indicator):
            return await future
        pending = asyncio.create_task(inspect_shared_dataset(state, resources, load))
        await asyncio.sleep(0)
        select_shared_asset(state, resources, 'other')
        select_shared_asset(state, resources, config.a.asset)
        future.set_result(DatasetDiscovery(config.a.evidence, config.a.images))
        self.assertFalse(await pending)
        self.assertIsNone(state.configuration.a.evidence)
        self.assertIsNone(state.configuration.b.evidence)


class RestoreSetupTests(unittest.TestCase):
    def test_close_undoes_edits_but_keeps_classes_found_for_the_same_asset(self):
        from mgci.application.landcover import restore_setup
        from mgci.domain.configuration import DatasetEvidence, TransitionTable
        opened = configuration()
        evidence = DatasetEvidence(opened.a.asset, ('lc/2000',), (10, 20), 'aoi', 'ready')
        edited = replace(opened, a=replace(opened.a, mapping=((10, 3),), evidence=evidence),
                         transition=TransitionTable(((1, 1, 2),), 'mine.csv', 'digest', True))
        restored = restore_setup(edited, opened)
        self.assertEqual(restored.a.mapping, opened.a.mapping)
        self.assertEqual(restored.transition, opened.transition)
        self.assertEqual(restored.a.evidence, evidence)

    def test_a_new_asset_returns_with_its_own_classes_and_years(self):
        from mgci.application.landcover import restore_setup
        opened = configuration()
        edited = replace(opened, a=replace(opened.a, asset='users/me/other', evidence=None, images=()))
        self.assertEqual(restore_setup(edited, opened).a, opened.a)
