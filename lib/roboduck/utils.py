"""Utility functions used by other roboduck modules."""

from collections.abc import Iterable
from colorama import Fore, Style
import difflib
import openai
import os
import pandas as pd
from pathlib import Path
import re
import warnings
import yaml


def colored(text, color):
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


def colordiff_new_str(old, new, color='green'):
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


def type_annotated_dict_str(dict_, func=repr):
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


def truncated_repr(obj, max_len=79):
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
    def qualname(obj):
        """Similar to type(obj).__qualname__() but that method doesn't always
        include the module(s). e.g. pandas Index has __qualname__ "Index" but
        this funnction returns "<pandas.core.indexes.base.Index>".
        """
        text = str(type(obj))
        names = re.search("<class '([a-zA-Z_.]*)'>", text).groups()
        assert len(names) == 1, f'Should have found only 1 qualname but ' \
                                f'found: {names}'
        return f'<{names[0]}>'

    open2close = {
        '[': ']',
        '(': ')',
        '{': '}'
    }
    repr_ = repr(obj)
    if len(repr_) < max_len:
        return repr_
    if isinstance(obj, pd.DataFrame):
        cols = truncated_repr(obj.columns.tolist(), max_len - 26)
        return f'pd.DataFrame(columns=' \
               f'{truncated_repr(cols, max_len - 22)})'
    if isinstance(obj, pd.Series):
        return f'pd.Series({truncated_repr(obj.tolist(), max_len - 11)})'
    if isinstance(obj, dict):
        length = 5
        res = ''
        for k, v in obj.items():
            if length >= max_len - 2:
                break
            new_str = f'{k!r}: {v!r}, '
            length += len(new_str)
            res += new_str
        return "{" + res.rstrip() + "...}"
    if isinstance(obj, str):
        return repr_[:max_len - 4] + "...'"
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
        n = int(max_len / len(repr_) * len(obj))
        if n == len(obj):
            # Even slicing to just first item is too long, so just revert
            # to treating this like a non-iterable object.
            return qualname(obj)
        # Need to slice set while keeping the original dtype.
        if isinstance(obj, set):
            slice_ = set(list(obj)[:n])
        else:
            try:
                slice_ = obj[:n]
            except Exception as e:
                warnings.warn(f'Failed to slice obj {obj}. Result may not be '
                              f'truncated as much as desired. Error:\n{e}')
                slice_ = obj
        repr_ = truncated_repr(slice_, max_len)
        non_brace_idx = len(repr_) - 1
        while repr_[non_brace_idx] in open2close.values():
            non_brace_idx -= 1
        if non_brace_idx <= 0 or (non_brace_idx == 3
                                  and repr_.startswith('set')):
            return repr_[:-1] + '...' + repr_[-1]
        return repr_[:non_brace_idx + 1] + ',...' + repr_[non_brace_idx + 1:]

    # We know it's non-iterable at this point.
    if isinstance(obj, type):
        return f'<class {obj.__name__}>'
    if isinstance(obj, (int, float)):
        return truncated_repr(format(obj, '.3e'), max_len)
    return qualname(obj)


def load_yaml(path, section=None):
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


def update_yaml(path, delete_if_none=True, **kwargs):
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


def extract_code(text, join_multi=True, multi_prefix_template='\n\n# {i}\n'):
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


def parse_completion(text):
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


def available_models():
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