"""Failures the user can act on, shown in the user's language."""

from typing import Callable, Optional

# The app's catalogue registers its lookup here (component.message), so this package
# does not import the UI. Without it, as in the offline tests, an error shows its key.
translate: Optional[Callable[..., str]] = None


class LocalizedError(ValueError):
    """A ValueError whose text is the catalogue message ``errors.<key>``.

    The text is looked up each time the error is shown, so a Solara render or task
    gets the user's language. A worker thread has no Solara context and gets English.
    """

    def __init__(self, key: str, **values):
        super().__init__(key)
        self.key = key
        self.values = values

    def __str__(self) -> str:
        if translate is None:
            return f'errors.{self.key}'
        return translate(f'errors.{self.key}', **self.values)
