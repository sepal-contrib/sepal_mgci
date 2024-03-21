import pandas as pd
import pytest

import component.parameter.directory as dir_
from component.parameter.module_parameter import TRANSITION_MATRIX_FILE, DECODE
from component.widget.transition_matrix import TransitionMatrix

# TODO: At some point I will have to change the way as v_model is set in each
# of the selectables.


@pytest.fixture
def transition_matrix():
    class Model:
        session_id = 1292

    model = Model()

    return TransitionMatrix(model)


def test_transition_matrix(transition_matrix):
    # Assert that transition matrix, matrix is the default
    assert transition_matrix.transition_matrix == str(TRANSITION_MATRIX_FILE)


def test_change_value(transition_matrix):
    """Check that new transition matrix file is created once any value is changed"""

    # Change value of transition matrix
    transition_matrix.get_children(id_="1_1")[0].v_model = {
        "row": 1,
        "col": 1,
        "value": 2,
    }

    suffix = transition_matrix.suffix

    # Check that new transition matrix file is created
    new_transition_file = dir_.TRANSITION_DIR / f"custom_transition_{suffix}.csv"

    assert new_transition_file.exists()

    # Read transition file and check that value row 1 and column 1 is 2

    edited_df = pd.read_csv(new_transition_file)

    assert (
        edited_df.loc[
            (edited_df.from_code == 1) & (edited_df.to_code == 1), "impact_code"
        ][0]
        == 2
    )

    # Check that default values are loaded when transition matrix is reset
    transition_matrix.set_default_values()

    # Read original transition matrix file and get value of row 1 and column 1

    default_df = pd.read_csv(TRANSITION_MATRIX_FILE)

    expected_value = default_df.loc[
        (default_df.from_code == 1) & (default_df.to_code == 1), "impact_code"
    ][0]

    assert transition_matrix.get_children(id_="1_1")[0].val.v_model == DECODE[
        expected_value
    ].get("abrv")
