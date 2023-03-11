import numpy as np
import pandas as pd
import pytest

from roboduck.utils import truncated_repr


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
    assert truncated_repr(obj) == repr(obj)


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
    assert truncated_repr(obj, n) == expected
