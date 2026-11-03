from pathlib import Path

import pandas as pd
import pytest
from traitlets import Dict, HasTraits, Unicode

from component.parameter.directory import dir_
from component.parameter.module_parameter import TRANSITION_MATRIX_FILE
from component.widget.transition_matrix import TransitionMatrix
from component.widget import transition_matrix as transition_module

# The widget works off the transition matrix that initialize_local()/
# initialize_remote() drop in the results dir (read and written from there at
# runtime), not the read-only packaged file.
DEFAULT_MATRIX = str(dir_.transition_dir / "transition_matrix.csv")


@pytest.fixture
def transition_matrix():
    class Model(HasTraits):
        session_id = 1292
        transition_matrix = Unicode()
        lulc_classes_sub_b = Dict()

    return TransitionMatrix(Model())


def impact_at(view, from_code, to_code):
    """Impact code the Vue widget currently shows for a (from, to) cell."""
    return next(
        cell["impact_code"]
        for cell in view.matrix_data
        if cell["from_code"] == from_code and cell["to_code"] == to_code
    )


def test_transition_matrix(transition_matrix):
    # Starts on the default transition matrix.
    assert transition_matrix.transition_matrix == DEFAULT_MATRIX


def test_custom_transition_mode_requires_an_explicit_selection(transition_matrix):
    transition_matrix.show_matrix = False
    assert transition_matrix.model.transition_matrix == ""

    transition_matrix.custom_transition_matrix.custom_transition_matrix = "selected.csv"
    assert transition_matrix.model.transition_matrix == "selected.csv"

    transition_matrix.transition_matrix_view.reset()
    assert transition_matrix.model.transition_matrix == "selected.csv"

    transition_matrix.show_matrix = True
    assert transition_matrix.model.transition_matrix == DEFAULT_MATRIX

    transition_matrix.show_matrix = False
    assert transition_matrix.model.transition_matrix == ""


@pytest.mark.parametrize("selection", ["", "invalid.csv"])
def test_cleared_or_invalid_selection_cannot_reuse_previous_file(
    transition_matrix, monkeypatch, selection
):
    transition_matrix.show_matrix = False
    custom = transition_matrix.custom_transition_matrix
    custom.custom_transition_matrix = "previous.csv"

    def invalid(*_):
        raise ValueError("Invalid transition file")

    monkeypatch.setattr(transition_module.validation, "validate_transition_matrix", invalid)
    change = {"new": selection, "owner": custom.input_impact}
    if selection:
        with pytest.raises(ValueError):
            custom.read_inputs(change)
    else:
        custom.read_inputs(change)
    assert transition_matrix.model.transition_matrix == ""


def test_change_value(transition_matrix):
    """Editing a cell writes a custom transition file; reset restores defaults."""
    view = transition_matrix.transition_matrix_view

    # Default impact for a stable (1 -> 1) transition is "Stable" (code 2); set a
    # different value so both the edit and the reset are observable.
    new_value = 1
    view.vue_cell_changed({"row": 1, "col": 1, "value": new_value})

    # A custom transition file is written to the results dir with the new value.
    custom_file = Path(view.custom_transition_file_path)
    assert custom_file.exists()

    edited_df = pd.read_csv(custom_file)
    changed = edited_df.loc[
        (edited_df.from_code == 1) & (edited_df.to_code == 1), "impact_code"
    ]
    assert changed.iloc[0] == new_value
    assert impact_at(view, 1, 1) == new_value

    # Resetting restores the packaged default for that cell.
    transition_matrix.set_default_values()

    default_df = pd.read_csv(TRANSITION_MATRIX_FILE)
    default_value = default_df.loc[
        (default_df.from_code == 1) & (default_df.to_code == 1), "impact_code"
    ].iloc[0]
    assert impact_at(view, 1, 1) == default_value
