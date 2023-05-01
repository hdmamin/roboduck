"""Utility functions used by other roboduck modules.
"""
from collections.abc import Iterable
from colorama import Fore, Style
import difflib
from functools import partial, wraps
import hashlib
import ipynbname
from inspect import signature, Parameter
from IPython.display import display, Javascript
from IPython import get_ipython
import openai
import json
import pandas as pd
from pathlib import Path
import re
import secrets
import time
import warnings
import yaml


def colored(text, color):
    """Add tags to color text and then reset color afterwards. Note that this
    does NOT actually print anything.

    Parameters
    ----------
    text: str
        Text that should be colored.
    color:
        Color name, e.g. "red". Must be available in the colorama lib. If None
        or empty str, just return the text unchanged.

    Returns
    -------
    str
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
    path = Path('/tmp')/f'{secrets.token_hex(24)}.txt'
    shell.magic(f'%history -n -f {path}')
    with open(path, 'r') as f:
        res = f.read()
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
        kind of str representation. Note that it is applied to each key/value
        as a whole, not to each item within that key/value. For example, notice
        below how foo and cat are not in quotes but ('bar',) and ['x'] do
        contain quotes.

        >>> d = {'foo': 'cat', ('bar',): ['x']}
        >>> type_annotated_dict_str(d, str)
        {
            foo: cat,   # type: str
            ('bar',): ['x'],   # type: list
        }

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
    path: str or Path
    section: str or None
        I vaguely recall yaml files can define different subsections. This lets
        you return a specific one if you want. Usually leave as None which
        returns the whole contents.

    Returns
    -------
    dict
    """
    with open(path, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data.get(section, data)


def typecheck(func_=None, **types):
    """Decorator to enforce type checking for a function or method. There are
    two ways to call this: either explicitly passing argument types to the
    decorator, or letting it infer them using type annotations in the function
    that will be decorated. We allow multiple both usage methods since older
    versions of Python lack type annotations, and also because I feel the
    annotation syntax can hurt readability.

    Ported from htools to avoid extra dependency.

    Parameters
    ----------
    func_: function
        The function to decorate. When using decorator with
        manually-specified types, this is None. Underscore is used so that
        `func` can still be used as a valid keyword argument for the wrapped
        function.
    types: type
        Optional way to specify variable types. Use standard types rather than
        importing from the typing library, as subscripted generics are not
        supported (e.g. typing.List[str] will not work; typing.List will but at
        that point there is no benefit over the standard `list`).

    Examples
    --------
    In the first example, we specify types directly in the decorator. Notice
    that they can be single types or tuples of types. You can choose to
    specify types for all arguments or just a subset.

    ```
    @typecheck(x=float, y=(int, float), iters=int, verbose=bool)
    def process(x, y, z, iters=5, verbose=True):
        print(f'z = {z}')
        for i in range(iters):
            if verbose: print(f'Iteration {i}...')
            x *= y
        return x
    ```

    >>> process(3.1, 4.5, 0, 2.0)
    TypeError: iters must be <class 'int'>, not <class 'float'>.

    >>> process(3.1, 4, 'a', 1, False)
    z = a
    12.4

    Alternatively, you can let the decorator infer types using annotations
    in the function that is to be decorated. The example below behaves
    equivalently to the explicit example shown above. Note that annotations
    regarding the returned value are ignored.

    ```
    @typecheck
    def process(x:float, y:(int, float), z, iters:int=5, verbose:bool=True):
        print(f'z = {z}')
        for i in range(iters):
            if verbose: print(f'Iteration {i}...')
            x *= y
        return x
    ```

    >>> process(3.1, 4.5, 0, 2.0)
    TypeError: iters must be <class 'int'>, not <class 'float'>.

    >>> process(3.1, 4, 'a', 1, False)
    z = a
    12.4
    """
    # Case 1: Pass keyword args to decorator specifying types.
    if not func_:
        return partial(typecheck, **types)
    # Case 2: Infer types from annotations. Skip if Case 1 already occurred.
    elif not types:
        types = {k: v.annotation
                 for k, v in signature(func_).parameters.items()
                 if not v.annotation == Parameter.empty}

    @wraps(func_)
    def wrapper(*args, **kwargs):
        fargs = signature(wrapper).bind(*args, **kwargs).arguments
        for k, v in types.items():
            if k in fargs and not isinstance(fargs[k], v):
                raise TypeError(
                    f'{k} must be {str(v)}, not {type(fargs[k])}.'
                )
        return func_(*args, **kwargs)
    return wrapper


def add_kwargs(func, fields, hide_fields=(), strict=False):
    """Decorator that adds parameters into the signature and docstring of a
    function that accepts **kwargs.

    Parameters
    ----------
    func: function
        Function to decorate.
    fields: list[str]
        Names of params to insert into signature + docstring.
    hide_fields: list[str]
        Names of params that are *already* in the function's signature that
        we want to hide. To use a non-empty value here, we must set strict=True
        and the param must have a default value, as this is what will be used
        in all subsequent calls.
    strict: bool
        If true, we do two things:
        1. On decorated function call, check that the user provided all
        expected arguments.
        2. Enable the use of the `hide_fields` param.

    Returns
    -------
    function
    """
    # Hide_fields must have default values in existing function. They will not
    # show up in the new docstring and the user will not be able to pass in a
    # value when calling the new function - it will always use the default.
    # To set different defaults, you can pass in a partial rather than a
    # function as the first arg here.
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    if hide_fields and not strict:
        raise ValueError(
            'You must set strict=True when providing one or more '
            'hide_fields. Otherwise the user can still pass in those args.'
        )
    sig = signature(wrapper)
    params_ = {k: v for k, v in sig.parameters.items()}

    # Remove any fields we want to hide.
    for field in hide_fields:
        if field not in params_:
            warnings.warn(f'No need to hide field {field} because it\'s not '
                          'in the existing function signature.')
        elif params_.pop(field).default == Parameter.empty:
            raise TypeError(
                f'Field "{field}" is not a valid hide_field because it has '
                'no default value in the original function.'
            )

    if getattr(params_.pop('kwargs', None), 'kind') != Parameter.VAR_KEYWORD:
        raise TypeError(f'Function {func} must accept **kwargs.')
    new_params = {
        field: Parameter(field, Parameter.KEYWORD_ONLY)
        for field in fields
    }
    overlap = set(new_params) & set(params_)
    if overlap:
        raise RuntimeError(
            f'Some of the kwargs you tried to inject into {func} already '
            'exist in its signature. This is not allowed because it\'s '
            'unclear how to resolve default values and parameter type.'
        )

    params_.update(new_params)
    wrapper.__signature__ = sig.replace(parameters=params_.values())
    if strict:
        # In practice langchain checks for this anyway if we ask for a
        # completion, but outside of that context we need typecheck
        # because otherwise we could provide no kwargs and _func wouldn't
        # complain. Just use generic type because we only care that a value is
        # provided.
        wrapper = typecheck(wrapper, **{f: object for f in fields})
    return wrapper


def extract_code(text, join_multi=True, multi_prefix_template='\n\n# {i}\n'):
    """Extract code snippet from a GPT response (e.g. from our `debug` chat
    prompt. See `Examples` for expected format.

    Parameters
    ----------
    text: str
    join_multi: bool
        If multiple code snippets are found, we can either choose to join them
        into one string or return a list of strings. If the former, we prefix
        each snippet with `multi_prefix_template` to make it clearer where
        each new snippet starts.
    multi_prefix_template: str
        If join_multi=True and multiple code snippets are found, we prepend
        this to each code snippet before joining into a single string. It
        should accept a single parameter {i} which numbers each code snippet
        in the order they were found in `text` (1-indexed).

    Returns
    -------
    str or list: code snippet from `text`. If we find multiple snippets, we
    either join them into one big string (if join_multi is True) or return a
    list of strings otherwise.

    Examples
    --------
    text = '''Appending to a tuple is not allowed because tuples are immutable.
    However, in this code snippet, the tuple b contains two lists, and lists
    are mutable. Therefore, appending to b[1] (which is a list) does not raise
    an error. To fix this, you can either change b[1] to a tuple or create a
    new tuple that contains the original elements of b and the new list.

    ```
    # Corrected code snippet
    a = 3
    b = ([0, 1], [2, 3])
    b = (b[0], b[1] + [a])
    ```'''
    print(extract_code(text))

    # Corrected code snippet
    a = 3
    b = ([0, 1], [2, 3])
    b = (b[0], b[1] + [a])
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
    text: str
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


def store_class_defaults(cls=None, attr_filter=None):
    """Class decorator that stores default values of class attributes (can be
    all or a subset). Default here refers to the value at class definition
    time.

    @store_class_defaults(attr_filter=lambda x: x.startswith('last_'))
    class Foo:
        last_bar = 3
        last_baz = 'abc'
        other = True

    >>> Foo._class_defaults

    {'last_bar': 3, 'last_baz': 'abc'}

    Or use the decorator without parentheses to store all values at definition
    time. This is usually unnecessary. If you do provide an attr_filter, it
    must be a named argument.

    Foo.reset_class_vars() will reset all relevant class vars to their
    default values.
    """
    if cls is None:
        return partial(store_class_defaults, attr_filter=attr_filter)
    if not isinstance(cls, type):
        raise TypeError(
            f'cls arg in store_class_defaults decorator has type {type(cls)} '
            f'but expected type `type`, i.e. a class. You may be passing in '
            f'an attr_filter as a positional arg which is not allowed - it '
            f'must be a named arg if provided.'
        )
    if not attr_filter:
        def attr_filter(x):
            return True
    defaults = {}
    for k, v in vars(cls).items():
        if attr_filter(k):
            defaults[k] = v

    name = '_class_defaults'
    if hasattr(cls, name):
        raise AttributeError(
            f'Class {cls} already has attribute {name}. store_class_defaults '
            'decorator would overwrite that. Exiting.'
        )
    setattr(cls, name, defaults)

    @classmethod
    def reset_class_vars(cls):
        """Reset all default class attributes to their defaults.
        """
        for k, v in cls._class_defaults.items():
            try:
                setattr(cls, k, v)
            except Exception as e:
                warnings.warn(f'Could not reset class attribute {k} to its '
                              f'default value:\n\n{e}')

    meth_name = 'reset_class_vars'
    if hasattr(cls, meth_name):
        raise AttributeError(
            f'Class {cls} already has attribute {meth_name}. '
            f'store_class_defaults decorator would overwrite that. Exiting.'
        )
    setattr(cls, meth_name, reset_class_vars)
    return cls


def available_models():
    """Show user available values for model_name parameter in debug.DuckDB
    class/ debug.duck function/errors.enable function etc.

    Returns
    -------
    dict[str, list[str]]: Maps provider name (e.g. 'openai') to list of valid
    model_name values. Provider name should correspond to a langchain or
    roboduck class named like ChatOpenai (i.e. Chat{provider.title()}).
    """
    res = {}

    # This logic may not always hold but as of April 2023, this returns
    # openai's available chat models.
    openai_res = openai.Model.list()
    res['openai'] = [row['id'] for row in openai_res['data']
                     if row['id'].startswith('gpt')]

    # TODO: add anthropic/cohere/other?
    return res


def is_ipy_name(
        name,
        count_as_true=('In', 'Out', '_dh', '_ih', '_ii', '_iii', '_oh')
):
    """Check if a variable name looks like an ipython output cell, e.g.
    "_49", "_", or "__".

    Ported from htools to avoid extra dependency.

    More examples:
    Returns True for names like (technically not sure if something like "__i3"
    is actually used in ipython, but it looks like something we probably want
    to remove in these contexts anyway /shrug):
    ['_', '__', '_i3', '__i3', '_4', '_9913', '__7', '__23874']

    Returns False for names like
    ['_a', 'i22', '__0i', '_03z', '__99t']
    and most "normal" variable names.

    Parameters
    ----------
    name: str
    count_as_true: Iterable[str]
        Additional variable names that don't necessarily fit the standard
        pattern but should nonetheless return True if we encounter them.

    Returns
    -------
    bool: True if it looks like an ipython output cell name, False otherwise.
    """
    # First check if it fits the standard leading underscore format.
    # Easier to handle the "only underscores" case separately because we want
    # to limit the number of underscores for names like "_i3".
    pat = '^_{1,2}i?\\d*$'
    is_under = bool(re.match(pat, name)) or not name.strip('_')
    return is_under or name in count_as_true


def add_docstring(func):
    """Add the docstring from another function/class to the decorated
    function/class.

    Ported from htools to avoid extra dependency.

    Examples
    --------
    ```
    @add_docstring(nn.Conv2d)
    class ReflectionPaddedConv2d(nn.Module):
        # ...
    ```
    """
    def decorator(new_func):
        new_func.__doc__ = f'{new_func.__doc__}\n\n{func.__doc__}'
        @wraps(new_func)
        def wrapper(*args, **kwargs):
            return new_func(*args, **kwargs)
        return wrapper
    return decorator
