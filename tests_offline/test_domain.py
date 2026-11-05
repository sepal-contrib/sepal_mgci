import unittest
from dataclasses import FrozenInstanceError, replace

from mgci.domain.codes import class_code, normalize_mapping
from mgci.domain.configuration import (
    Configuration, DatasetEvidence, ImageSelection, IndicatorConfig,
    ScalePolicy, TransitionTable, Workflow,
)
from mgci.domain.validation import readiness
from mgci.domain.provenance import scientific_identity


def configuration():
    images = (ImageSelection('lc/2000', 2000), ImageSelection('lc/2015', 2015),
              ImageSelection('lc/2018', 2018))
    evidence = DatasetEvidence('lc', ('lc/2000', 'lc/2015', 'lc/2018'),
                               (10, 20), 'aoi', 'ready')
    indicator = IndicatorConfig('lc', evidence, ((10, 1), (20, 2)),
                                (1, 2), images)
    transition = TransitionTable(((1, 1, 2), (1, 2, 1), (2, 1, 3), (2, 2, 2)),
                                 'matrix.csv', 'digest', True)
    return Configuration('aoi', Workflow.CUSTOM_RECLASSIFY, indicator, indicator,
                         transition=transition)


class CodesTests(unittest.TestCase):
    def test_numeric_strings_are_integers_without_fraction_truncation(self):
        for raw in ('10', '10.0', 10, '1e1'):
            self.assertEqual(class_code(raw), 10)
        for raw in ('10.1', float('nan'), 'Infinity', True, None, ''):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                class_code(raw)

    def test_normalized_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mapping([('10', 1), (10, 2)])
        self.assertEqual(normalize_mapping([('20', '2'), ('10', '1')]),
                         ((10, 1), (20, 2)))


class ReadinessTests(unittest.TestCase):
    def test_complete_configuration_can_execute_each_indicator(self):
        for indicator in ('a', 'b'):
            self.assertTrue(readiness(configuration(), indicator, 'statistics').ready)

    def test_missing_explicit_file_only_blocks_b(self):
        config = replace(configuration(), transition=None)
        self.assertTrue(readiness(config, 'a', 'statistics').ready)
        self.assertIn('transition_required', self.codes(config, 'b'))
        implicit = replace(configuration().transition, explicitly_selected=False)
        self.assertIn('transition_required', self.codes(replace(config, transition=implicit), 'b'))

    def test_all_questionnaire_branches(self):
        config = configuration()
        for workflow in (Workflow.DEFAULT, Workflow.DEFAULT_EDIT_TRANSITIONS):
            standard = replace(config, workflow=workflow,
                               transition=replace(config.transition, explicitly_selected=False))
            self.assertTrue(readiness(standard, 'b', 'statistics').ready)
        canonical = replace(config.a, mapping=(),
                            evidence=replace(config.a.evidence, classes=(1, 2)))
        no_remap = replace(config, workflow=Workflow.CUSTOM_CANONICAL,
                           a=canonical, b=canonical)
        self.assertTrue(readiness(no_remap, 'b', 'statistics').ready)
        default_raw = replace(canonical, asset=config.default_asset,
                              evidence=replace(canonical.evidence, asset=config.default_asset))
        self.assertIn('default_raw_asset', self.codes(replace(no_remap, a=default_raw)))

    def test_omitted_source_and_unassigned_target_block_execution(self):
        for mapping, expected in ((((10, 1),), 'mapping_incomplete'),
                                  (((10, 0), (20, 0)), 'mapping_unassigned'),
                                  (((10, 1), (20, 999)), 'unknown_target'),
                                  (((10, 1), (20, 3)), 'unknown_target')):
            config = configuration()
            self.assertIn(expected, self.codes(replace(config, a=replace(config.a, mapping=mapping))))

    def test_empty_row_is_masked_out_not_blocked(self):
        # As the legacy app: target 0 is masked by no_remap, and the table warns about it.
        config = configuration()
        self.assertEqual(self.codes(replace(config, a=replace(config.a, mapping=((10, 1), (20, 0))))), set())

    def test_loading_empty_or_wrong_scope_discovery_is_not_readiness(self):
        config = configuration()
        for evidence in (replace(config.a.evidence, status='loading'),
                         replace(config.a.evidence, classes=()),
                         replace(config.a.evidence, aoi_identity='old'),
                         replace(config.a.evidence, images=('lc/2000',))):
            self.assertFalse(readiness(replace(config, a=replace(config.a, evidence=evidence)),
                                       'a', 'statistics').ready)

    def test_transition_requires_complete_pairs_and_valid_impacts(self):
        config = configuration()
        for rows in (((1, 1, 2), (2, 2, 2)),
                     config.transition.rows + ((1, 1, 2),),
                     ((1, 1, 0), (1, 2, 1), (2, 1, 3), (2, 2, 2))):
            table = replace(config.transition, rows=rows)
            self.assertIn('invalid_transition', self.codes(replace(config, transition=table), 'b'))

    def test_b_periods_and_membership_are_validated(self):
        config = configuration()
        for images in (config.b.images[:1], tuple(reversed(config.b.images)),
                       (ImageSelection('elsewhere', 2000), *config.b.images[1:])):
            self.assertFalse(readiness(replace(config, b=replace(config.b, images=images)),
                                       'b', 'statistics').ready)

    def test_setup_can_precede_year_selection(self):
        config = configuration()
        config = replace(config, a=replace(config.a, images=()))
        self.assertTrue(readiness(config, 'a', 'setup').ready)
        self.assertFalse(readiness(config, 'a', 'statistics').ready)

    def test_native_and_custom_empty_are_distinct(self):
        config = configuration()
        self.assertTrue(readiness(config, 'a', 'statistics').ready)
        for value in (None, 9, 1501):
            self.assertIn('scale_range', self.codes(replace(config, scale=ScalePolicy('custom', value))))
        for value in (10, 100, 300, 500, 1000, 1500):
            self.assertTrue(readiness(replace(config, scale=ScalePolicy('custom', value)),
                                      'a', 'statistics').ready)

    def test_immutable_inputs_cannot_retain_mutable_lists(self):
        config = configuration()
        with self.assertRaises(FrozenInstanceError):
            config.a.asset = 'changed'
        with self.assertRaises(TypeError):
            replace(config.a, mapping=[[10, 1]])

    @staticmethod
    def codes(config, indicator='a'):
        return {issue.code for issue in readiness(config, indicator, 'statistics').issues}


class IdentityTests(unittest.TestCase):
    def test_b_transition_changes_do_not_change_a_identity(self):
        config = configuration()
        changed = replace(config, transition=replace(config.transition, content_digest='new'))
        self.assertEqual(scientific_identity(config, 'a', 'statistics'),
                         scientific_identity(changed, 'a', 'statistics'))
        self.assertNotEqual(scientific_identity(config, 'b', 'statistics'),
                            scientific_identity(changed, 'b', 'statistics'))

    def test_metadata_change_does_not_recalculate_numbers(self):
        config = configuration()
        self.assertEqual(scientific_identity(config, 'a', 'statistics'),
                         scientific_identity(replace(config, source='New source'), 'a', 'statistics'))

    def test_area_settings_affect_statistics_but_not_categorical_layers(self):
        config = configuration()
        changed = replace(config, rsa=True, dem='other-dem')
        self.assertEqual(scientific_identity(config, 'a', 'layer'),
                         scientific_identity(changed, 'a', 'layer'))
        self.assertNotEqual(scientific_identity(config, 'a', 'statistics'),
                            scientific_identity(changed, 'a', 'statistics'))


class DiscoveryContractTests(unittest.TestCase):
    def test_noncanonical_discovered_classes_cannot_certify_readiness(self):
        config = configuration()
        for classes in ((True, 2), (1.0, 2), ('1', 2), (1, 1, 2)):
            indicator = replace(config.a, mapping=(),
                                evidence=replace(config.a.evidence, classes=classes))
            candidate = replace(config, workflow=Workflow.CUSTOM_CANONICAL, a=indicator)
            self.assertFalse(readiness(candidate, 'a', 'statistics').ready)

    def test_compatible_mapping_rows_survive_narrower_discovery(self):
        config = configuration()
        narrowed = replace(config.a, evidence=replace(config.a.evidence, classes=(10,)))
        self.assertTrue(readiness(replace(config, a=narrowed), 'a', 'statistics').ready)


class PackagedClassificationTests(unittest.TestCase):
    def test_a_accepts_all_ten_packaged_classes(self):
        config = configuration()
        for target in (7, 8, 9, 10):
            candidate = replace(config.a, targets=tuple(range(1, 11)), mapping=((10, 1), (20, target)))
            self.assertTrue(readiness(replace(config, a=candidate), 'a', 'statistics').ready)
        invalid = replace(config.a, targets=(1, 11), mapping=((10, 1), (20, 11)))
        self.assertFalse(readiness(replace(config, a=invalid), 'a', 'statistics').ready)


class YearRowScopeTests(unittest.TestCase):
    def test_empty_year_row_does_not_block_land_cover_setup(self):
        from mgci.domain.validation import readiness
        config = configuration()
        config = replace(config, a=replace(config.a, images=(*config.a.images, ImageSelection('', 0))))
        self.assertTrue(readiness(config, 'a', 'setup').ready)
        codes = [issue.code for issue in readiness(config, 'a', 'statistics').issues]
        self.assertIn('years_required', codes)
        self.assertNotIn('stale_images', codes)

    def test_image_from_another_asset_blocks_outputs_only(self):
        from mgci.domain.validation import readiness
        config = configuration()
        config = replace(config, a=replace(config.a, images=(ImageSelection('other/2000', 2000),)))
        self.assertTrue(readiness(config, 'a', 'setup').ready)
        self.assertEqual(readiness(config, 'a', 'statistics').issues[0].code, 'stale_images')


class PackagedMappingTests(unittest.TestCase):
    def test_default_flow_masks_classes_missing_from_packaged_mapping(self):
        from mgci.domain.configuration import Workflow
        from mgci.domain.validation import readiness
        config = configuration()
        evidence = replace(config.a.evidence, classes=(0, 10, 20))
        for workflow, ready in ((Workflow.DEFAULT, True), (Workflow.CUSTOM_RECLASSIFY, False)):
            changed = replace(config, workflow=workflow, a=replace(config.a, evidence=evidence))
            with self.subTest(workflow=workflow):
                codes = [issue.code for issue in readiness(changed, 'a', 'setup').issues]
                self.assertEqual('mapping_incomplete' not in codes, ready)
