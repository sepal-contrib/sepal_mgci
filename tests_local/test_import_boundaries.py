import subprocess
import sys
import unittest


class ImportBoundaryTests(unittest.TestCase):
    def test_adapter_imports_do_not_authenticate_or_write_user_files(self):
        script = '''
import os
from pathlib import Path
from unittest.mock import patch
os.environ.pop('DEPLOY_ENV', None)
original_mkdir = Path.mkdir
def guarded_mkdir(path, *args, **kwargs):
    if 'module_results' in path.parts:
        raise AssertionError('Import must not create user directories')
    return original_mkdir(path, *args, **kwargs)
with patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')), \\
     patch('ee.data.get_persistent_credentials', side_effect=AssertionError('Credentials forbidden')), \\
     patch('ee.Initialize', side_effect=AssertionError('Import must not initialize EE')), \\
     patch.object(Path, 'mkdir', guarded_mkdir), \\
     patch('shutil.copy', side_effect=AssertionError('Import must not overwrite files')):
    import component.solara.scale
    import component.solara.app
    import mgci.infrastructure.science
    from mgci.infrastructure.reports import build_workbook
    try:
        build_workbook(())
    except ValueError:
        pass
    else:
        raise AssertionError('Empty workbook must be rejected')
'''
        completed = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
