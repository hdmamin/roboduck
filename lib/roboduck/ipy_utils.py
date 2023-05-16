"""Functions related to loading, saving, or otherwise working with ipython
sessions or jupyter notebooks.
"""
import hashlib
import json
import re
import secrets
import time
from pathlib import Path

import ipynbname
from IPython import get_ipython
from IPython.core.display import display, Javascript


def load_ipynb(path, save_if_self=True):
    """Loads ipynb and formats cells into 1 big string.

    Adapted from htools.cli.ReadmeUpdater method.

    Parameters
    ----------
    path : Path
        Path to notebook to load.
    save_if_self : bool
        If True, check if this is being called from the current notebook. If
        so, save it. (If not, we never save - auto saving is only intended to
        address the scenario where we're in an active notebook and call this
        function before recent changes have been saved. The load_ipynb call
        itself means that at least 1 change has inevitably occurred since
        saving.)

    Returns
    -------
    str
        Code contents of notebook. Each cell is enclosed in triple backticks
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
        if not cell['source']:
            continue
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
    formatted : bool
        If True, format list of cells into a single str like this (note: if
        you don't see any backticks below, know that each print statement is
        enclosed in a separate pair of triple backticks. Rendering this nicely
        with mkdocs is very tricky and even if it worked, it would badly mess
        up readability for people viewing the docstring in their IDE):

        '''
        ```
        print('This is cell 1 code.')
        ```

        ```
        print('This is cell 2 code.')
        ```
        '''

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


def is_ipy_name(
        name,
        count_as_true=('In', 'Out', '_dh', '_ih', '_ii', '_iii', '_oh')
):
    """```plaintext
    Check if a variable name looks like an ipython output cell name, e.g.
    "_49", "_", or "__".

    Ported from [htools](https://github.com/hdmamin/htools) to avoid extra
    dependency.

    More examples:
    Returns True for names like this (technically not sure if something like
    "__i3" is actually used in ipython, but it looks like something we
    probably want to remove it in these contexts anyway.
    ['_', '__', '_i3', '__i3', '_4', '_9913', '__7', '__23874']

    Returns False for names like
    ['_a', 'i22', '__0i', '_03z', '__99t']
    and most "normal" variable names.
    ```

    Parameters
    ----------
    name : str
        The variable name to check.
    count_as_true : Iterable[str]
        Additional variable names that don't necessarily fit the standard
        pattern but should nonetheless return True if we encounter them.

    Returns
    -------
    bool
        True if it looks like an ipython output cell name, False otherwise.
    """
    # First check if it fits the standard leading underscore format.
    # Easier to handle the "only underscores" case separately because we want
    # to limit the number of underscores for names like "_i3".
    pat = '^_{1,2}i?\\d*$'
    is_under = bool(re.match(pat, name)) or not name.strip('_')
    return is_under or name in count_as_true


def save_notebook(file_path):
    """Save a jupyter notebook. We use this in load_ipynb (optionally) to
    ensure that when we load a notebook's source
    code, we get the most up to date version. Adapted from
    https://stackoverflow.com/questions/32237275/save-an-ipython-notebook-programmatically-from-within-itself/57814673#57814673

    Parameters
    ----------
    file_path : str
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