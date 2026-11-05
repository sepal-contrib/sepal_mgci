"""Toast timing for the app, on top of pysepal's 3 s defaults."""

from pysepal.solara.notifications import TOAST_TIMEOUT_DEFAULTS, ToastType

# Error toasts stay until the user clicks them.
TOAST_TIMEOUT_DEFAULTS[ToastType.ERROR] = None

# Seconds for a toast that names a saved file or a task, long enough to read the path.
LASTING = 8.0
