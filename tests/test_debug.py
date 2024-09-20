import pytest

from roboduck.debug import DuckDB


@pytest.mark.parametrize(
    'line,expected',
    (
        ('?', True),
        ('Why is this happening?', True),
        ('??? weird', True),
        ('Can you explain this?', True),
        ('> ok that makes sense', True),
        ('>ok that makes sense', True),
        ('ok that makes sense >', False),
        ('ok that makes sense', False),
        ('print("Hello")', False),
        ('n', False),
        ('next', False),
        ('c', False),
        ('continue', False),
        ('p x', False),
        ('x < 5', False),
    )
)
def test_is_conversational_reply(line: str, expected: bool):
    debugger = DuckDB()
    assert debugger._is_conversational_reply(line) == expected


@pytest.mark.parametrize(
        'key,expected_names',
        (
            (None,
             {'code', 'global_vars', 'local_vars', 'next_line', 'question'}),
            ('contextful',
             {'code', 'global_vars', 'local_vars', 'next_line', 'question'}),
            ('contextless',
             {'question'}),
        )
)
def test_field_names(key: str, expected_names: 'set[str]'):
    debugger = DuckDB()
    kwargs = {}
    if key is not None:
        kwargs['key'] = key
    field_names = debugger.field_names(**kwargs)
    assert field_names == expected_names