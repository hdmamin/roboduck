"""Command line tool that allows us to run files with explainable error mode
enabled without changing the file itself (perhaps not that useful given that
errors mode can be enabled with a single import, but just another option).
This file needs to be stashed in roboduck/cli subdir to avoid circular
import error caused by logging.py name collision with standard library.
"""
import argparse
import ast
from pathlib import Path
import subprocess


def make_import_statement(cls_name):
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


def run():
    """Execute a python script with auto error mode enabled.

    Run a python script with roboduck's errors mode
    automatically enabled.

    Examples
    --------
    Make sure to include the equals sign between option name and value.
    If using a custom chat_class, the full name must be provided.

    ```
    duck my_script.py
    duck my_script.py --chat_class=roboduck.DummyChatClass
    duck my_script.py --auto=True --prompt_name=~/my_custom_prompt.yaml
    ```
    """
    parser = argparse.ArgumentParser(
        description=run.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('file', help='The python script to execute.')
    args, kwargs_ = parser.parse_known_args()
    kwargs = {}
    imports = []
    for x in kwargs_:
        if not (x.startswith('--') and '=' in x):
            raise ValueError(f'Malformed command. Encountered {x!r} when '
                             'parsing command but expected format like '
                             '--key=val.')
        k, v = x.split('=')
        k = k.strip('--')
        if k in ('cls', 'chat_class'):
            imports.append(make_import_statement(v))
            kwargs[k] = v.rpartition('.')[-1]
        else:
            kwargs[k] = ast.literal_eval(v)

    # Grab source code and insert our imports and enable error mode.
    path = Path(args.file).resolve()
    tmp_path = Path('/tmp')/path.name
    with open(path, 'r') as f:
        src_text = f.read()
    new_text = 'from roboduck import errors\n' + '\n'.join(imports) + '\n'
    if kwargs:
        kwargs_str = ''
        for k, v in kwargs.items():
            kwargs_str += f'{k}='
            if k in ('cls', 'chat_class'):
                kwargs_str += v
            else:
                kwargs_str += repr(v)
            kwargs_str += ', '
        new_text += f'errors.enable(**dict({kwargs_str}))\n'
    modified_text = new_text + src_text

    # Create copy file with imports and errors enabled, try to execute it, then
    # restore original file. Keep all file renaming and writing inside try
    # block to avoid confusion caused by premature sigints.
    try:
        path.rename(tmp_path)
        with open(path, 'w') as f:
            f.write(modified_text)
        subprocess.call(['python', str(path)])
    except Exception as e:
        raise e
    # At one point I observed an error where a sigint during error explanation
    # resulted in tmp_path not being found and the file at the user-specified
    # path was left with the roboduck errors import. I believe moving the
    # `path.rename` step inside the try block fixed that but to be safe,
    # we add some additional error handling.
    finally:
        if tmp_path.is_file():
            tmp_path.rename(path)
        else:
            with open(path, 'w') as f:
                f.write(src_text)


if __name__ == '__main__':
    run()
