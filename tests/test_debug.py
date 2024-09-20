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
def test_DuckDB_is_conversational_reply(line: str, expected: bool):
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
def test_DuckDB_field_names(key: str, expected_names: 'set[str]'):
    debugger = DuckDB()
    kwargs = {}
    # Want to reflect what happens if we literally pass in nothing.
    if key is not None:
        kwargs['key'] = key
    field_names = debugger.field_names(**kwargs)
    assert field_names == expected_names


@pytest.mark.parametrize(
        'line,warns',
        (
            ('SyntaxError(abc)', True),
            ('raise NameError(def)', True),
            ('c', False),
            ('what\'s going on?', False),
        )
)
def test_DuckDB_error(line: str, warns: bool, capsys):
    debugger = DuckDB()
    debugger.error(line)
    stdout = capsys.readouterr()
    did_warn = 'If you meant to respond to Duck in natural ' \
        'language' in stdout.out
    assert did_warn == warns


@pytest.mark.parametrize(
        'source_code,cleaned_code',
        (
            (
                "def foo():\n    x = 1\n    duck()\n    y = 2\n    return x + y",
                "def foo():\n    x = 1\n    y = 2\n    return x + y"
            ),
            (
                "print('Hello')\nduck(silent=True)\nprint('World')",
                "print('Hello')\nprint('World')"
            ),
            (
                "duck()\nif True:\n    duck()\n    print('test')",
                "if True:\n    print('test')"
            ),
            (
                "x = 5\n# duck() in a comment should be ignored\nduck()\ny = 10",
                "x = 5\n# duck() in a comment should be ignored\ny = 10"
            ),
            (
                "def bar():\n    return 'No duck calls here'",
                "def bar():\n    return 'No duck calls here'"
            ),
        )
)
def test_DuckDB_remove_debugger_call(source_code: str, cleaned_code: str):
    debugger = DuckDB()
    assert debugger._remove_debugger_call(source_code) == cleaned_code