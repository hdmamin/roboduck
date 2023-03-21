"""Utility functions used by other roboduck modules.
"""
from collections.abc import Iterable
from colorama import Fore, Style
import difflib
import hashlib
import ipynbname
from IPython.display import display, Javascript
from IPython import get_ipython
import json
import pandas as pd
from pathlib import Path
import re
import time

from htools.core import random_str, load


def colored(text, color):
    """Add tags to color text and then reset color afterwards. Note that this
    does NOT actually print anything.

    Parameters
    ----------
    text: str
        Text that should be colored.
    color:
        Color name, e.g. "red". Must be available in the colorama lib.

    Returns
    -------
    str
    """
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
    old: str
        This is what `new` is compared to when identifying differences.
    new: str
        Determines content of output str.
    color: str
        Text color for new characters.

    Returns
    -------
    str: Same content as `new` but color new parts in a different color.
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


def save_notebook(file_path):
    """Save a jupyter notebook. We use this in load_ipynb (optionally) to
    ensure that when we load a notebook's source
    code, we get the most up to date version. Adapted from
    https://stackoverflow.com/questions/32237275/save-an-ipython-notebook-programmatically-from-within-itself/57814673#57814673

    Parameters
    ----------
    file_path: str
        Path to notebook that you want to save.
    """

    def file_md5(path):
        with open(path, 'rb') as f:
            text = f.read()
        return hashlib.md5(text).hexdigest()

    start_md5 = file_md5(file_path)
    display(Javascript('IPython.notebook.save_checkpoint();'))
    current_md5 = start_md5

    while start_md5 == current_md5:
        time.sleep(1)
        current_md5 = file_md5(file_path)


def load_ipynb(path, save_if_self=True):
    """Loads ipynb and formats cells into 1 big string.

    Adapted from htools.cli.ReadmeUpdater method.

    Parameters
    ----------
    path: Path
        Path to notebook to load.
    save_if_self: bool
        If True, check if this is being called from the current notebook. If
        so, save it. (If not, we never save - auto saving is only intended to
        address the scenario where we're in an active notebook and call this
        function before recent changes have been saved. The load_ipynb call
        itself means that at least 1 change has inevitably occurred since
        saving.)

    Returns
    -------
    str: Code contents of notebook. Each cell is enclosed in triple backticks
    and separated by newlines.
    """
    if save_if_self:
        try:
            self_path = ipynbname.path()
        except FileNotFoundError:
            pass
        else:
            if self_path == path:
                save_notebook(path)

    with open(path, 'r') as f:
        cells = json.load(f)['cells']

    cell_str = ''
    for cell in cells:
        if not cell['source']: continue
        source = '\n' + ''.join(cell['source']) + '\n'
        if cell['cell_type'] == 'code':
            source = '\n```' + source + '```\n'
        cell_str += source
    return cell_str


def load_current_ipython_session(formatted=True):
    """Load current ipython session as a list and optionally convert it to a
    nicely formatted str with each cell enclosed in triple backticks.

    Parameters
    ----------
    formatted: bool
        If True, format list of cells into a single str like:

        ```
        print('This is cell 1 code.')
        ```

        ```
        print('This is cell 2 code.')
        ```

        If False, leave it as a list of strings where each string contains
        content from one cell.

    Returns
    -------
    list or str
    """
    shell = get_ipython()
    path = Path('/tmp')/f'{random_str(24)}.txt'
    shell.magic(f'%history -n -f {path}')
    res = load(path)
    path.unlink()
    cells = []
    for row in res.splitlines():
        content = row.partition(':')[-1].strip()
        if content:
            cells.append(content)
    if formatted:
        return '\n\n'.join(f'```\n{cell}\n```' for cell in cells)
    return cells


def type_annotated_dict_str(dict_, func=repr):
    """String representation (or repr) of a dict, where each line includes
    an inline comment showing the type of the value.

    Parameters
    ----------
    dict_: dict
        The dict to represent.
    func: function
        The function to apply to each key and value in the dict to get some
        kind of str representation.

    Returns
    --------
    str
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
    obj: any
    max_len: int
        Max number of characters for resulting repr. Think of this more as an
        estimate than a hard guarantee - precision isn't important in our use
        case. The result will likely be shorter than this because we want to
        truncate in a readable place, e.g. taking the repr of the first k items
        of a list instead of taking the repr of all items and then slicing off
        the end of the repr.

    Returns
    -------
    str: Repr for obj, truncated to approximately max_len characters or fewer.
    When possible, we insert ellipses into the repr to show that truncation
    occurred. Technically there are some edge cases we don't handle (e.g. if
    obj is a class with an insanely long name) but that's not a big deal, at
    least at the moment. I can always revisit that later if necessary.
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
            slice_ = obj[:n]
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
