"""All the process that can be run using nox.

The nox run are build in isolated environment that will be stored in .nox. to force the venv update, remove the .nox/xxx folder.
"""

from pathlib import Path

import nox


@nox.session(reuse_venv=True)
def lint(session):
    """Apply the pre-commits."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--a", *session.posargs)


@nox.session(reuse_venv=True)
def app(session):
    """Run the application."""

    entry_point = str(Path("ui.ipynb"))

    # Duplicate the entry point file
    session.run("cp", entry_point, "nox_ui.ipynb")

    # change the kernel name in the entry point
    session.run("entry_point", "--test", "nox_ui.ipynb")

    session.run("jupyter", "trust", entry_point)
    session.run(
        "voila", "--show_tracebacks=True", "--template=sepal-ui-base", "nox_ui.ipynb"
    )


@nox.session(reuse_venv=True)
def jupyter(session):
    """Run the application."""
    session.install("-r", "requirements.txt")
    session.run("jupyter", "trust", "no_ui.ipynb")
    session.run("jupyter", "notebook", "no_ui.ipynb")
