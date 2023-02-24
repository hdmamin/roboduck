import pdb
import sys
import traceback

from htools import monkeypatch
from roboduck.utils import colored
from roboduck.debugger import RoboDuckDB, roboduck


@monkeypatch(sys, 'excepthook')
def excepthook(type_, val, tb):
    """Replaces sys.excepthook when module is imported, which makes us enter
    a debugging session whenever an error is thrown. Disable by calling
    autodebug.disable().
    """
    traceback.print_exception(type_, val, tb)
    while True:
        prompt = colored(
            '[RoboDuck] Shall I explain this error message? [y/n]\n',
            'green'
        )
        cmd = input(prompt).lower()
        if cmd == 'y':
            # TODO: query gpt3
            print('QUERYING GPT3')
            pdb.post_mortem(tb, Pdb=RoboDuckDB)
            return
        if cmd == 'n':
            return
        print(f'Encountered unrecognized command {cmd!r}.')


# TODO delete
print(9 + 'a')
