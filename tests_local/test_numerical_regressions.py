"""Run the sub-indicator B numerical regressions without the pytest Earth Engine fixtures."""

from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

from mgci.infrastructure.transitions import parse_transition


class NumericalRegressionTests(unittest.TestCase):
    def test_existing_b_numerical_regressions(self):
        with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')):
            cases = runpy.run_path('tests/test_scripts/test_sub_b.py')
            matrix = parse_transition(Path('component/parameter/transition_matrix.csv').read_bytes(), 'packaged.csv')
            for name, case in cases.items():
                if name.startswith('test_') and callable(case):
                    with self.subTest(case=name):
                        case(matrix)
