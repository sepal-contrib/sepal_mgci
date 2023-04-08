import pandas as pd


def validate_file(file_, text_field_msg, type_):
    """Read user inputs from custom transition matrix and custom green/non green"""

    try:
        # Read csv file
        df = pd.read_csv(file_)
        # remove white spaces from column names
        df.columns = df.columns.str.strip()

    except pd.errors.ParserError:
        # Raise a more specific error for when the file cannot be parsed as a csv
        error_msg = (
            "The file could not be read. Please check that the file is a valid csv file"
        )
        text_field_msg.error_messages = error_msg
        raise ValueError(error_msg)

    except FileNotFoundError:
        # Raise a more specific error for when the file cannot be found
        error_msg = "The file could not be found. Please check the file path."
        text_field_msg.error_messages = error_msg
        raise ValueError(error_msg)

    # Define column requirements for each type
    column_requirements = {
        "impact": {
            "required_cols": ["from_code", "to_code", "impact_code"],
            "int_cols": ["from_code", "to_code", "impact_code"],
            "allowed_values": {"impact_code": [0, -1, 1]},
        },
        "green": {
            "required_cols": ["lc_class", "green"],
            "int_cols": ["lc_class", "green"],
            "allowed_values": {"green": [0, 1]},
        },
    }

    # Get column requirements for the given type
    req_cols = column_requirements.get(type_, {}).get("required_cols", [])
    allowed_values = column_requirements.get(type_, {}).get("allowed_values", {})

    # Check that the file contains the required columns
    if not set(req_cols).issubset(df.columns):
        error_msg = (
            f"The file must contain the following columns: {', '.join(req_cols)}"
        )
        text_field_msg.error_messages = error_msg
        raise ValueError(error_msg)

    # Check that all values are integers
    for col in df.columns:
        if not pd.api.types.is_integer_dtype(df[col]):

            error_msg = f"The {col} column must contain only integer values."
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

    # Check that there are no values outside the allowed values in the column requirements
    for col, allowed_vals in allowed_values.items():
        if not set(df[col].unique()).issubset(allowed_vals):

            join_vals = ", ".join([str(val) for val in allowed_vals])
            error_msg = (
                f"The {col} column must contain only the following values: {join_vals}"
            )
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

    # If type_ == "impact", check that the from_code and to_code columns doesn't
    # have repeated values.
    if type_ == "impact":
        if len(df) != len(df.drop_duplicates(subset=["from_code", "to_code"])):
            error_msg = (
                f"The from_code and to_code columns must not have repeated values."
            )
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

    # If type_ == "green", check that the lc_class column doesn't have repeated values.
    if type_ == "green":
        if len(df) != len(df.drop_duplicates(subset=["lc_class"])):
            error_msg = f"The lc_class column must not have repeated values."
            text_field_msg.error_messages = error_msg
            raise ValueError(error_msg)

    return file_
