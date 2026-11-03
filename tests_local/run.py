"""Run dependency tests with all network and persistent EE credentials forbidden."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden in local tests')), patch(
    'ee.data.get_persistent_credentials', side_effect=AssertionError('Persistent credentials forbidden in local tests')
):
    suite = unittest.defaultTestLoader.discover(str(root / 'tests_local'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
