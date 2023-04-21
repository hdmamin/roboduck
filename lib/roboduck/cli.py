import argparse
import ast
import importlib
from pathlib import Path
import subprocess


def import_class(full_name):
    module_name, _, cls_name = full_name.rpartition('.')
    module = importlib.import_module(module_name)
    return getattr(module, cls_name)


def run():
    parser = argparse.ArgumentParser(
        description='Run a python script with roboduck\'s errors mode '
                    'automatically enabled. Example:\n\nduck my_script.py'
    )
    parser.add_argument('file', help='The python script to execute.')
    args, kwargs_ = parser.parse_known_args()
    kwargs = {}
    for x in kwargs_:
        if not (x.startswith('--') and '=' in x):
            raise ValueError(f'Malformed command. Encountered {x!r} when '
                             'parsing command but expected format like '
                             '--key=val.')
        k, v = x.split('=')
        k = k.strip('--')
        if k in ('cls', 'chat_class'):
            # TODO: weird circular import error related to logging. Also occurs
            # even if I manually import (not using importlib) the module and/or
            # if I import a lib that itself imports logging, e.g. numpy or
            # requests. Also happens if import occurs outside this function.
            # kwargs[k] = import_class(v)
            raise NotImplementedError(f'Support for option `{k}` has not'
                                      ' yet been implemented.')
        else:
            kwargs[k] = ast.literal_eval(v)
    path = Path(args.file).resolve()
    tmp_path = Path('/tmp')/path.name
    with open(path, 'r') as f:
        src_text = f.read()
    path.rename(tmp_path)
    new_text = 'from roboduck import errors\n'
    if kwargs:
        new_text += f'errors.enable(**{kwargs})\n'
    src_text = new_text + src_text

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
