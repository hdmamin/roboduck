import numpy as np
import pandas as pd
import pytest
from textwrap import dedent

import roboduck.decorators
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


@pytest.mark.parametrize(
    'obj, n, expected',
    [
        (
            [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            50,
            "[[1, 2, 3], [4, 5, 6], [7, 8, 9]]"
        ),
        (
            [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]],
            40,
            "<list, truncated_data=[[1, 2, 3], [4, 5, 6], [7, 8, 9], ...], len=4>"
        ),
        (
            [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}, {'e': 5, 'f': 6}],
            50,
            "[{'a': 1, 'b': 2}, {'c': 3, 'd': 4}, {'e': 5, 'f': 6}]"
        ),
        (
            [{'a': 1, 'b': 2}, {'c': 3, 'd': 4}, {'e': 5, 'f': 6}],
            30,
            "<list, truncated_data=[{'a': 1, 'b': 2}, ...], len=3>"
        ),
        (
            {'x': list(range(100 * i)) for i in range(10)},
            30,
            # TODO: fix the bug this revealed, currently I think this always
            # displays the whole first value so repr is way too long.
        )
    ]
)
def test_truncated_repr_nested_inputs(obj, n, expected):
    assert utils.truncated_repr(obj, n) == expected


@pytest.mark.parametrize(
    "d, func, expected",
    [
        ({}, repr, '{\n}'),
        ({'a': 1, 'b': 'two', 'c': 3}, repr, "{\n    'a': 1,   # type: int\n    'b': 'two',   # type: str\n    'c': 3,   # type: int\n}"),
        ({'x': 1.23, 'y': True, 'z': False}, repr, "{\n    'x': 1.23,   # type: float\n    'y': True,   # type: bool\n    'z': False,   # type: bool\n}"),
        ({'foo': 'cat', 'bar': {'x': 'dog', 'y': 3}}, str, "{\n    foo: cat,   # type: str\n    bar: {'x': 'dog', 'y': 3},   # type: dict\n}"),
    ]
)
def test_type_annotated_dict_str(d, func, expected):
    assert utils.type_annotated_dict_str(d, func) == expected


@pytest.mark.parametrize("text, join_multi, expected_output", [
    ("No code snippet here.", True, ""),
    ("```python\nprint('Code only')\n```", True, "print('Code only')"),
    ("```\nprint('Multiple code snippets')\n```\n```python\nprint('another one')\n```", True, "# 1\nprint('Multiple code snippets')\n\n# 2\nprint('another one')"),
    ("```python\nprint('Hello, World!')\n```\n```python\nprint('Goodbye, World!')\n```", False, ["print('Hello, World!')", "print('Goodbye, World!')"])
])
def test_extract_code(text, join_multi, expected_output):
    assert utils.extract_code(text, join_multi) == expected_output


def test_extract_code_with_backticks_in_code():
    completion = dedent('''
    Stuff before code.
    ```
    def parse():
        """
        This docstring contains single and triple backticks. This variant has 
        a single newline char before the first triple backticks. Do the thing 
        with variables `x` and `y`. Then run this snippet:
        ```
        y = api_call()
        z = 33
        ```
        """
        return
    ```
    ''').strip()

    expected = dedent('''
    def parse():
        """
        This docstring contains single and triple backticks. This variant has 
        a single newline char before the first triple backticks. Do the thing 
        with variables `x` and `y`. Then run this snippet:
        ```
        y = api_call()
        z = 33
        ```
        """
        return
    ''').strip()
    assert utils.extract_code(completion) == expected


def test_store_class_defaults():
    @roboduck.decorators.store_class_defaults(attr_filter=lambda x: x.startswith('last_'))
    class Foo:
        last_bar = 3
        last_baz = 'abc'
        other = True

    assert Foo._class_defaults == {'last_bar': 3, 'last_baz': 'abc'}

    Foo.last_bar = 4
    Foo.last_baz = 'xyz'
    Foo.other = False

    # `other` should be unaffected by reset, others should return to defaults.
    Foo.reset_class_vars()
    assert Foo.last_bar == 3
    assert Foo.last_baz == 'abc'
    assert Foo.other is False


@pytest.mark.parametrize(
    "obj,answer",
    (
        ({3: 4}, False),
        ([2, 3], False),
        ([], False),
        (('a', 'b', 'c'), False),
        ('pandas.Series', False),
        (pd.DataFrame, False),
        (pd.Series, False),
        (pd.DataFrame({"a": [3, 5]}), False),
        (pd.DataFrame(), False),
        # TODO: series currently return True, consider making func stricter
        # OR maybe removing hardcoded series if block and refactor so
        # existing is_array_like block handles it?
        (pd.Series([1, 2, 3]), False),
        (pd.Series([1.0, None]), False),
        (pd.Series(), False),
        (np.arange(5), True),
        (np.array([]), True),
    )
)
def test_is_array_like(obj, answer):
    assert utils.is_array_like(obj) == answer


@pytest.mark.parametrize(
    "obj,with_brackets,expected",
    [
        (pd.DataFrame(), False, "pandas.core.frame.DataFrame"),
        (pd.Series(), False, "pandas.core.series.Series"),
        (np.array([]), False, "numpy.ndarray"),
        ([], False, "list"),
        ({}, False, "dict"),
        (pd.DataFrame(), True, "<pandas.core.frame.DataFrame>"),
        (pd.Series(), True, "<pandas.core.series.Series>"),
        (np.array([]), True, "<numpy.ndarray>"),
        ([], True, "<list>"),
        ({}, True, "<dict>"),
    ]
)
def test_qualname(obj, with_brackets, expected):
    assert utils.qualname(obj, with_brackets=with_brackets) == expected
