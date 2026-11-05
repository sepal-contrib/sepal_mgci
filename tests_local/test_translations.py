"""French and Spanish catalogues, and the text that follows the user's language."""

import ast
import json
import unittest
from pathlib import Path

import ipyvuetify as v
import solara
from pysepal.i18n import set_locale

from component.message import messages
from component.solara.scale import ScaleField
from mgci.domain.configuration import ScalePolicy
from mgci.errors import LocalizedError

ROOT = Path(__file__).resolve().parents[1]


def walk(widget):
    yield widget
    for child in getattr(widget, 'children', ()) or ():
        if not isinstance(child, str):
            yield from walk(child)


def localized_error_keys():
    """Every literal key given to LocalizedError in the app's code."""
    keys = set()
    for path in (*ROOT.glob('mgci/**/*.py'), *ROOT.glob('component/**/*.py')):
        for node in ast.walk(ast.parse(path.read_text())):
            if (isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'LocalizedError'
                    and node.args and isinstance(node.args[0], ast.Constant)):
                keys.add(node.args[0].value)
    return keys


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        set_locale('en')

    def test_app_ships_complete_french_and_spanish(self):
        self.assertEqual(messages.available_locales(), ('en', 'es', 'fr'))
        # check() also reports keys a locale lacks, so this proves full coverage.
        self.assertEqual(messages.check(), ())

    def test_every_localized_error_has_an_english_message(self):
        errors = json.loads((ROOT / 'component/message/en/app.json').read_text())['errors']
        keys = localized_error_keys()
        self.assertGreater(len(keys), 30)
        self.assertEqual(sorted(keys - set(errors)), [])

    def test_error_text_follows_the_locale(self):
        error = LocalizedError('report_not_calculated', indicator='B')
        self.assertIsInstance(error, ValueError)
        self.assertEqual(str(error), 'Calculate sub-indicator B before downloading its report')
        set_locale('es')
        self.assertEqual(str(error), 'Calcula el subindicador B antes de descargar su informe.')

    def test_component_rerenders_when_the_language_changes(self):
        set_locale('es')

        @solara.component
        def Harness():
            ScaleField(ScalePolicy(), lambda value: None)

        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)

        def texts():
            field = next(w for w in walk(root) if isinstance(w, v.TextField))
            native = next(w for w in walk(root) if isinstance(w, v.Btn) and w.value == 0)
            return field.placeholder, native.children[0]

        self.assertEqual(texts(), ('Personalizada', 'Nativa'))
        set_locale('fr')
        self.assertEqual(texts(), ('Personnalisée', 'Native'))
