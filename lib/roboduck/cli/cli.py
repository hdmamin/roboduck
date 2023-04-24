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
    cls_name: str
        Class name including module (essentially __qualname__?), e.g.
        roboduck.debug.DuckDB.

    Returns
    -------
    str
    """
    parts = cls_name.split('.')
    if len(parts) == 1:
        return f'import {parts[0]}'
    else:
        lib = '.'.join(parts[:-1])
        return f'from {lib} import {parts[-1]}'


def run():
    parser = argparse.ArgumentParser(
        description='Run a python script with roboduck\'s errors mode '
                    'automatically enabled.\n\nExamples:\n\nduck my_script.py'
                    '\nduck my_script.py --chat_class=roboduck.DummyChatClass'
                    '\nduck my_script.py --auto=True '
                    '--prompt_name=~/my_custom_prompt.yaml',
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
    path.rename(tmp_path)
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
    src_text = new_text + src_text

    # Create copy file with imports and errors enabled, try to execute it, then
    # restore original file.
    try:
        with open(path, 'w') as f:
            f.write(src_text)
        subprocess.call(['python', str(path)])
    except Exception as e:
        raise e
    finally:
        tmp_path.rename(path)


if __name__ == '__main__':
    run()
