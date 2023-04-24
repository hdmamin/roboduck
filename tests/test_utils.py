import numpy as np
import pandas as pd
import pytest

from roboduck import utils


@pytest.mark.parametrize(
    'obj',
    [
        list(range(10)),
        {char: i for i, char in enumerate('abcdef')},
        True,
        7,
        "a"
    ]
)
def test_truncated_repr_short_inputs(obj):
    assert utils.truncated_repr(obj) == repr(obj)


@pytest.mark.parametrize(
    'obj, n, expected',
    [
        (list(range(1000)),
         50,
         "[0, 1, 2, 3, 4, 5, 6, 7, 8, 9,...]"),
        (pd.DataFrame(np.arange(390).reshape(30, 13),
                      columns=list('abcdefghijklm')),
         79,
         "pd.DataFrame(columns=\"['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',"
         " 'i', 'j',...]\")"),
        ("abcdefghijklmnopqrstuvwxyz", 20, "'abcdefghijklmno...'"),
        (dict(enumerate('abcdefghijklmnop')),
         50,
         "{0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f',...}")
    ]
)
def test_truncated_repr_long_inputs(obj, n, expected):
    assert utils.truncated_repr(obj, n) == expected


# TODO: gpt-generated test. Think the last case may not have correct output due
# its custom format func. Need to check that once I get pytest working again,
# started getting import error recently.
@pytest.mark.parametrize(
    "d, func, expected",
    [
        ({}, repr, '{}'),
        ({'a': 1, 'b': 'two', 'c': 3}, repr, "{\n    'a': 1,   # type: int\n    'b': 'two',   # type: str\n    'c': 3,   # type: int\n}"),
        ({'x': 1.23, 'y': True, 'z': False}, repr, "{\n    'x': 1.23,   # type: float\n    'y': True,   # type: bool\n    'z': False,   # type: bool\n}"),
        ({'foo': [1, 2, 3], 'bar': {'x': 4, 'y': 5}}, lambda x: f"'{x}'", "{\n    'foo': [1, 2, 3],   # type: list\n    'bar': {'x': 4, 'y': 5},   # type: dict\n}"),
    ]
)
def test_type_annotated_dict_str(d, func, expected):
    assert utils.type_annotated_dict_str(d, func) == expected
