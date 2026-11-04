"""All the process that can be run using nox.

The nox run are build in isolated environment that will be stored in .nox. to force the venv update, remove the .nox/xxx folder.
"""

from pathlib import Path
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from jupyter_client.kernelspec import KernelSpecManager
import nox


@nox.session(reuse_venv=True)
def lint(session):
    """Apply the pre-commits."""
    session.install("pre-commit")
    session.run("pre-commit", "run", "--a", *session.posargs)


@nox.session(reuse_venv=True)
def test_ui(session):
    """Import the Solara entry point in the module venv kernel, as SEPAL starts it."""

    root_folder = Path(__file__).parent
    notebook = nbformat.v4.new_notebook()
    notebook.cells = [nbformat.v4.new_code_cell("import solara_app\nsolara_app.Page")]
    ksm = KernelSpecManager()
    print(list(ksm.get_all_specs()))
    ep = ExecutePreprocessor(timeout=600, kernel_name=f"test-{root_folder.name}")
    ep.preprocess(notebook, {"metadata": {"path": str(root_folder)}})


@nox.session()
def test(session):
    test_files = session.posargs or ["tests"]
    session.install("-r", "requirements.txt")
    session.install("pytest-cov")
    session.run("pytest", "--color=yes", "--cov", "--cov-report=xml", *test_files)
    if not session.posargs:
        session.run("python", "-S", "-m", "unittest", "discover", "-s", "tests_offline")
        session.run("python", "tests_local/run.py")
