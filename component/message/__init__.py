"""The app's message catalogue: every user-facing string, looked up with msg("dotted.key")."""

from pathlib import Path

from pysepal.i18n import catalog

messages = catalog(Path(__file__).parent)
msg = messages.msg
