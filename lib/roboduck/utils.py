"""Utility functions used by other roboduck modules."""

from collections.abc import Iterable
from colorama import Fore, Style
import difflib
from functools import wraps
import openai
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Union
import yaml


def colored(text: str, color: str) -> str:
    """Add tags to color text and then reset color afterwards. Note that this
    does NOT actually print anything.

    Parameters
    ----------
    text : str
        Text that should be colored.
    color : str
        Color name, e.g. "red". Must be available in the colorama lib. If None
        or empty str, just return the text unchanged.

    Returns
    -------
    str
        Note that you need to print() the result for it to show up in the
        desired color. Otherwise it will just have some unintelligible
        characters appended and prepended.
    """
    if not color:
        return text
    color = getattr(Fore, color.upper())
    return f'{color}{text}{Style.RESET_ALL}'


def colordiff_new_str(old: str, new: str, color: str = 'green') -> str:
    """Given two strings, return the new one with new parts in green. Note that
    deletions are ignored because we want to retain only characters in the new
    string. Remember colors are only displayed correctly when printing the
    resulting string - otherwise it just looks like we added extra junk
    characters.

    Idea is that when displaying a revised code snippet from gpt, we want to
    draw attention to the new bits.

    Adapted from this gist + variations in comments:
    https://gist.github.com/ines/04b47597eb9d011ade5e77a068389521

    Parameters
    ----------
    old : str
        This is what `new` is compared to when identifying differences.
    new : str
        Determines content of output str.
    color : str
        Text color for new characters.

    Returns
    -------
    str
        Same content as `new` but color new parts in a different color.
    """
    res = []
    matcher = difflib.SequenceMatcher(None, old, new)
    for opcode, s1, e1, s2, e2 in matcher.get_opcodes():
        if opcode == 'delete':
            continue
        chunk = new[s2:e2]
        if opcode in ('insert', 'replace'):
            chunk = colored(chunk, color)
        res.append(chunk)
    return ''.join(res)


def type_annotated_dict_str(dict_: Dict, func: Callable = repr) -> str:
    """String representation (or repr) of a dict, where each line includes
    an inline comment showing the type of the value.

    Parameters
    ----------
    dict_ : dict
        The dict to represent.
    func : function
        The function to apply to each key and value in the dict to get some
        kind of str representation. Note that it is applied to each key/value
        as a whole, not to each item within that key/value. See examples.

    Returns
    -------
    str

    Examples
    --------
    Notice below how foo and cat are not in quotes but ('bar',) and ['x'] do
    contain quotes.
    >>> d = {'foo': 'cat', ('bar',): ['x']}
    >>> type_annotated_dict_str(d, str)
    {
        foo: cat,   # type: str
        ('bar',): ['x'],   # type: list
    }
    """
    type_strs = [f'\n    {func(k)}: {func(v)},   # type: {type(v).__name__}'
                 for k, v in dict_.items()]
    return '{' + ''.join(type_strs) + '\n}'


def is_array_like(obj: Any) -> bool:
    """Hackily check if obj is a numpy array/torch tensor/pd.Series or similar
    without requiring all those libraries as dependencies
    (notably, pd.DataFrame is not considered array_like - it has useful column
    names unlike these other types).
    Instead of checking for specific types here, we just check that the obj
    has certain attributes that those objects should have.
    If obj is the class itself rather than an instance, we return False.
    """
    return all(hasattr(obj, attr)
               for attr in ("ndim", "shape", "dtype", "tolist")) \
            and not isinstance(obj, type)


def qualname(obj: Any, with_brackets: bool = True) -> str:
    """Similar to type(obj).__qualname__() but that method doesn't always
    include the module(s). e.g. pandas Index has __qualname__ "Index" but
    this function returns "<pandas.core.indexes.base.Index>".

    Set with_brackets=False to skip the leading/trailing angle brackets.
    """
    text = str(type(obj))
    names = re.search("<class '([a-zA-Z_.]*)'>", text).groups()
    assert len(names) == 1, f'Should have found only 1 qualname but ' \
                            f'found: {names}'
    if with_brackets:
        return f'<{names[0]}>'
    return names[0]


def format_listlike_with_metadata(
        array: Iterable, truncated_data: Optional[Iterable] = None
    ) -> str:
    """Format a list-like object with metadata.

    This function creates a string representation of a list-like object,
    including its class name, truncated data (if provided), and additional
    metadata such as shape, dtype, or length.

    Parameters
    ----------
    array : object
        The list-like object to be formatted.
    truncated_data : object, optional
        A truncated version of the array's data. If provided, it will be
        included in the formatted string.

    Returns
    -------
    str
        A formatted string representation of the array with metadata.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.array([1, 2, 3, 4, 5])
    >>> format_listlike_with_metadata(arr, arr[:3])
    '<numpy.ndarray, truncated_data=[1, 2, 3, ...], shape=(5,), dtype=int64>'

    >>> import pandas as pd
    >>> series = pd.Series(['a', 'b', 'c', 'd', 'e'])
    >>> format_listlike_with_metadata(series, series[:2])
    "<pandas.core.series.Series, truncated_data=['a', 'b', ...], len=5>"
    """
    open2close = {
        '(': ')',
        '{': '}',
        '[': ']',
    }
    closing_bracket_str = ''.join(open2close.values())
    clsname = qualname(array, with_brackets=False)
    res = f"<{clsname}, truncated_data="
    if truncated_data is None:
        truncated_data = '[...]'

    if is_array_like(array):
        if isinstance(truncated_data, str):
            res += truncated_data
        else:
            repr_ = repr(truncated_data.tolist())
            res += f"{repr_[:-1] + repr_[-1].rstrip(closing_bracket_str)}, " \
                   f"...{open2close.get(repr_[0], '')}"
        res += f", shape={array.shape}, dtype={array.dtype}>"
        return res

    # Duplicating logic but maybe not that important to clean this up,
    # context lengths are increasing anyway so maybe we won't need all this
    # truncated_repr related stuff much longer.
    # This lets us pass in a str for truncated data - when we do, we don't want
    # to reattach the closing bracket, as we would if passing in a
    # list/set/tuple.
    if isinstance(truncated_data, str):
        res += truncated_data
    else:
        repr_ = repr(truncated_data)
        # If the last char is a closing brace, we want to strip it. But we
        # don't want to strip multiple closing braces, e.g. [(3, 4), (5, 6)].
        res += f"{repr_[:-1] + repr_[-1].rstrip(closing_bracket_str)}, " \
                f"...{open2close.get(repr_[0], '')}"
    return res + f", len={len(array)}>"  # type: ignore


def fallback(*, default: Optional[Any] = None,
             default_func: Optional[Callable] = None) -> Callable:
    """Decorator to provide a default value (or function that produces a value)
    to return when the decorated function's execution fails.

    You must specify either default OR default_func, not both. If default_func
    is provided, it should accept the same args as the decorated function.
    """
    if bool(default) + bool(default_func) != 1:
        raise ValueError('Exactly 1 of ()`default`, `default_func`) args '
                         'must be non-None.')

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if default is not None:
                    return default
                return default_func(*args, **kwargs)
        return wrapper

    return decorator


@fallback(default_func=qualname)
def truncated_repr(obj: Any, max_len: int = 400) -> str:
    """Return an object's repr, truncated to ensure that it doesn't take up
    more characters than we want. This is used to reduce our chances of using
    up all our available tokens in a gpt prompt simply communicating that a
    giant data structure exists, e.g. list(range(1_000_000)). Our use
    case doesn't call for anything super precise so the max_len should be
    thought of as more of guide than an exact max. I think it's enforced but I
    didn't put a whole lot of thought or effort into confirming that.

    Parameters
    ----------
    obj : any
    max_len : int
        Max number of characters for resulting repr. Think of this more as an
        estimate than a hard guarantee - precision isn't important in our use
        case. The result will likely be shorter than this because we want to
        truncate in a readable place, e.g. taking the repr of the first k items
        of a list instead of taking the repr of all items and then slicing off
        the end of the repr.

    Returns
    -------
    str
        Repr for obj, truncated to approximately max_len characters or fewer.
        When possible, we insert ellipses into the repr to show that truncation
        occurred. Technically there are some edge cases we don't handle (e.g.
        if obj is a class with an insanely long name) but that's not a big
        deal, at least at the moment. I can always revisit that later if
        necessary.
    """
    repr_ = repr(obj)
    if len(repr_) < max_len:
        return repr_

    if isinstance(obj, str):
        return repr_[:max_len - 16] + "...' (truncated)"

    if isinstance(obj, Iterable):
        # A bit risky but sort of elegant. Just recursively take smaller
        # slices until we get an acceptable length. We may end up going
        # slightly over the max length after adding our ellipses but it's
        # not that big a deal, this isn't meant to be super precise. We
        # can also end up with fewer items than we could have fit - if we
        # exhaustively check every possible length one by one until we
        # find the max length that fits, we can get a very slow function
        # when inputs are long.
        # Can't easily pass smaller max_len value into recursive call
        # because we always want to compare to the user-specified value.
        # n is the approximate number of items we expect to be able to fit in
        # a truncated repr of length <= max_len, though this is of course not
        # bulletproof (usually only a problem for nested or multidimensional
        # data structures).
        n = max(1, int(max_len / len(repr_) * len(obj)))  # type: ignore

        # Need to slice set while keeping the original dtype.
        if isinstance(obj, set):
            slice_ = set(list(obj)[:n])
        elif isinstance(obj, dict):
            slice_ = list(obj.items())[:n]
        else:
            slice_ = obj[:n]  # type: ignore

        if n == len(obj):
            # Slicing didn't help in this case so do some manual surgery.
            # Don't call truncated_repr recursively here because we would
            # get stuck in an infinite loop because there's no room to slice
            # our object to be shorter.
            # Arbitrarily choosing to subtract 10 to account for some the
            # characters created by qualname and attributres, could try to do
            # this more carefully but don't think it's worth it right now.
            # We then slice up to the last comma to ensure we don't truncate
            # mid item, e.g. [10, 20, 30] should not be truncated to '[10, 2'.
            truncated_str = repr(slice_)[:max_len - 10]
            truncated_str = truncated_str[:truncated_str.rfind(',')]
            return format_listlike_with_metadata(
                obj,
                truncated_data=truncated_str
            )

        return format_listlike_with_metadata(obj, truncated_data=slice_)

    # We know it's non-iterable at this point.
    if isinstance(obj, type):
        return f'<class {obj.__name__}>'
    
    # Note that ints/floats usually won't hit this block, but it could happen
    # with an extraordinarily high number of digits.
    if isinstance(obj, (int, float)):
        return truncated_repr(format(obj, '.3e'), max_len)
    return qualname(obj)


def load_yaml(path: Union[str, Path], section: Optional[str] = None) -> Dict:
    """Load a yaml file. Useful for loading prompts.

    Borrowed from jabberwocky.

    Parameters
    ----------
    path : str or Path
    section : str or None
        I vaguely recall yaml files can define different subsections. This lets
        you return a specific one if you want. Usually leave as None which
        returns the whole contents.

    Returns
    -------
    dict
    """
    with open(path, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader) or {}
    return data.get(section, data)


def update_yaml(path: Union[str, Path], delete_if_none: bool = True,
                **kwargs) -> None:
    """Update a yaml file with new values.

    Parameters
    ----------
    path : str or Path
        Path to yaml file to update. If it doesn't exist, it will be created.
        Any necessary intermediate directories will be created too.
    delete_if_none : bool
        If True, any k-v pairs in kwargs where v is None will be treated as an
        instruction to delete key k from the yaml file. If False, we will
        actually set `{field}: None` in the yaml file.
    kwargs : any
        Key-value pairs to update the yaml file with.
    """
    path = Path(path).expanduser()
    os.makedirs(path.parent, exist_ok=True)
    try:
        data = load_yaml(path)
    except FileNotFoundError:
        data = {}
    for k, v in kwargs.items():
        if v is None and delete_if_none:
            data.pop(k, None)
        else:
            data[k] = v
    with open(path, 'w') as f:
        yaml.dump(data, f)


def extract_code(
    text: str,
    join_multi: bool = True,
    multi_prefix_template: str = '\n\n# {i}\n'
) -> Union[str, List]:
    """Extract code snippet from a GPT response (e.g. from our `debug` chat
    prompt. See `Examples` for expected format.

    Parameters
    ----------
    text : str
    join_multi : bool
        If multiple code snippets are found, we can either choose to join them
        into one string or return a list of strings. If the former, we prefix
        each snippet with `multi_prefix_template` to make it clearer where
        each new snippet starts.
    multi_prefix_template : str
        If join_multi=True and multiple code snippets are found, we prepend
        this to each code snippet before joining into a single string. It
        should accept a single parameter {i} which numbers each code snippet
        in the order they were found in `text` (1-indexed).

    Returns
    -------
    str or list
        Code snippet from `text`. If we find multiple snippets, we either join
        them into one big string (if join_multi is True) or return a
        list of strings otherwise.

    Examples
    --------
    ```plaintext
    text = '''Appending to a tuple is not allowed because tuples are immutable.
    However, in this code snippet, the tuple b contains two lists, and lists
    are mutable. Therefore, appending to b[1] (which is a list) does not raise
    an error. To fix this, you can either change b[1] to a tuple or create a
    new tuple that contains the original elements of b and the new list.

    ```python
    # Corrected code snippet
    a = 3
    b = ([0, 1], [2, 3])
    b = (b[0], b[1] + [a])
    ```'''

    print(extract_code(text))

    # Extracted code snippet
    '''
    a = 3
    b = ([0, 1], [2, 3])
    b = (b[0], b[1] + [a])
    '''
    ```
    """
    chunks = re.findall("(?s)```(?:python)?\n(.*?)\n```", text)
    if not join_multi:
        return chunks
    if len(chunks) > 1:
        chunks = [multi_prefix_template.format(i=i) + chunk
                  for i, chunk in enumerate(chunks, 1)]
        chunks[0] = chunks[0].lstrip()
    return ''.join(chunks)


def parse_completion(text: str) -> Dict:
    """This function is called on the gpt completion text in
    roboduck.debug.DuckDB.ask_language_model (i.e. when the user asks a
    question during a debugging session, or when an error occurs when in
    auto-explain errors mode).

    Users can define their own custom function as a replacement (mostly
    useful when defining custom prompts too). The only requirements are that
    the function must take 1 string input and return a dict containing the
    keys "explanation" and "code", with an optional key "extra" that can be
    used to store any additional information (probably in a dict). For example,
    if you wrote a prompt that asked gpt to return valid json, you could
    potentially use json.loads() as your drop-in replacement (ignoring
    validation/error handling, which you might prefer to handle via a langchain
    chain anyway).

    Parameters
    ----------
    text : str
        GPT completion. This should contain both a natural language explanation
        and code.

    Returns
    -------
    dict[str]
    """
    # Keep an eye out for how this performs - considered going with a more
    # complex regex or other approach here but since part 2 is supposed to be
    # code only, maybe that's okay. Extract_code could get weird if gpt
    # uses triple backticks in a function docstring but that should be very
    # rare, and the instructions sort of discourage it.
    explanation = text.partition('\n```')[0]
    code = extract_code(text)
    return {'explanation': explanation,
            'code': code}


def available_models() -> Dict:
    """Show user available values for model_name parameter in debug.DuckDB
    class/ debug.duck function/errors.enable function etc.

    Returns
    -------
    dict[str, list[str]]
        Maps provider name (e.g. 'openai') to list of valid
        model_name values. Provider name should correspond to a langchain or
        roboduck class named like ChatOpenai (i.e. Chat{provider.title()}).
        Eventually would like to support other providers like anthropic but
        never got off API waitlist.
    """
    # Weirdly, env var is set and available but openai can't seem to find it
    # unless we explicitly set it here.
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    res = {}

    # This logic may not always hold but as of April 2023, this returns
    # openai's available chat models.
    openai_res = openai.Model.list()
    res['openai'] = [row['id'] for row in openai_res['data']
                     if row['id'].startswith('gpt')]
    return res


def make_import_statement(cls_name: str) -> str:
    """Given a class name like 'roboduck.debug.DuckDB', construct the import
    statement (str) that should likely be used to import that class (in this
    case 'from roboduck.debug import DuckDB'.

    Parameters
    ----------
    cls_name : str
        Class name including module (essentially __qualname__?), e.g.
        roboduck.DuckDB. (Note that this would need to be roboduck.debug.DuckDB
        if we didn't include DuckDB in roboduck's __init__.py.)

    Returns
    -------
    str
        E.g. "from roboduck import DuckDB"
    """
    parts = cls_name.split('.')
    if len(parts) == 1:
        return f'import {parts[0]}'
    else:
        lib = '.'.join(parts[:-1])
        return f'from {lib} import {parts[-1]}'
