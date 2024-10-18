"""Utility functions for testing scripts."""

from math import isclose
from numbers import Number


def sort_dict_lists(data):
    if isinstance(data, dict):
        # Recursively process each value in the dictionary
        return {k: sort_dict_lists(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Check if the list contains dictionaries
        if all(isinstance(item, dict) for item in data):
            # Determine the key to sort on based on available keys
            if all("biobelt" in item for item in data):
                # Sort by 'biobelt' key
                return sorted(
                    [sort_dict_lists(item) for item in data], key=lambda x: x["biobelt"]
                )
            elif all("lc" in item for item in data):
                # Sort by 'lc' key
                return sorted(
                    [sort_dict_lists(item) for item in data], key=lambda x: x["lc"]
                )
            else:
                # Recursively process each item without sorting
                return [sort_dict_lists(item) for item in data]
        else:
            # Recursively process each item without sorting
            return [sort_dict_lists(item) for item in data]
    else:
        # Return the data as is if it's neither a dict nor a list
        return data


def compare_nested_dicts(dict1: dict, dict2: dict, rel_tol=1e-7):
    """Recursively compare two dictionaries or lists, allowing for float comparisons with tolerance."""

    # sort the dictionaries
    dict1 = sort_dict_lists(dict1)
    dict2 = sort_dict_lists(dict2)

    if isinstance(dict1, dict) and isinstance(dict2, dict):
        for key in dict1:
            assert key in dict2, f"Key '{key}' not found in second dictionary"
            compare_nested_dicts(dict1[key], dict2[key], rel_tol)
    elif isinstance(dict1, list) and isinstance(dict2, list):
        assert len(dict1) == len(dict2), "Lists are of different lengths"
        for item1, item2 in zip(dict1, dict2):
            compare_nested_dicts(item1, item2, rel_tol)
    elif isinstance(dict1, Number) and isinstance(dict2, Number):
        # Use isclose for approximate comparison of numbers
        assert isclose(
            dict1, dict2, rel_tol=rel_tol
        ), f"{dict1} and {dict2} are not approximately equal"
    else:
        assert dict1 == dict2, f"{dict1} and {dict2} are not equal"

    return True
