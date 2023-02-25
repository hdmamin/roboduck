# Prototyped method to auto ask basic question without requiring user to type
# it. Elegant but probably not the most functional - we don't actually pass the
# stack trace or error to gpt, so it's just inferring what the issue is.
from htools import monkeypatch
from IPython import get_ipython
from roboduck.debugger import RoboDuckDB
import sys
from traceback import TracebackException


def my_post_mortem(trace, t=None, Pdb=RoboDuckDB):
    if t is None:
        t = sys.exc_info()[2]
        assert t is not None, "post_mortem outside of exception context"

    p = Pdb()
    p.reset()
    # TODO: rm dev mode
    p.cmdqueue.insert(0, '[dev] What caused this error?')
    p.cmdqueue.insert(1, 'q')
    # TODO start
    print(f'IN POST MORTEM\n{trace}\nEND TRACE')
    # TODO end
    p.interaction(None, t)


def ipy_excepthook(self, etype, evalue, tb, tb_offset):
    """IPython doesn't use sys.excepthook. We have to handle this separately
    and make sure it expects the right arguments.
    """
    return excepthook(etype, evalue, tb)


def my_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    """Print exception up to 'limit' stack trace entries from 'tb' to 'file'.

    This differs from print_tb() in the following ways: (1) if
    traceback is not None, it prints a header "Traceback (most recent
    call last):"; (2) it prints the exception type and value after the
    stack trace; (3) if type is SyntaxError and value has the
    appropriate format, it prints the line where the syntax error
    occurred with a caret on the next line indicating the approximate
    position of the error.
    """
    # format_exception has ignored etype for some time, and code such as cgitb
    # passes in bogus values as a result. For compatibility with such code we
    # ignore it here (rather than in the new TracebackException API).
    if file is None:
        file = sys.stderr
    trace = ''.join(
        TracebackException(type(value), value, tb, limit=limit)
        .format(chain=chain)
    )
    # TODO: maybe rm file option? Not sure when that gets used.
    if file != sys.stderr:
        with open(file, 'w') as f:
            f.write(trace)
    return trace


@monkeypatch(sys, 'excepthook')
def excepthook(etype, val, tb):
    """Replaces sys.excepthook when module is imported, which makes us enter
    a debugging session whenever an error is thrown. Disable by calling
    autodebug.disable().
    """
    trace = my_print_exception(etype, val, tb)
    print(trace)
    while True:
        cmd = input('Explain error message? [y/n]\n').lower()
        if cmd == 'y':
            return my_post_mortem(trace, tb)
        if cmd == 'n':
            return
        print('Unrecognized command. Valid choices are "y" or "n".\n')


# Only necessary/possible when in ipython.
try:
    get_ipython().set_custom_exc((Exception,), ipy_excepthook)
except AttributeError:
    pass


def fancy_mod(x):
    for i, num in enumerate(x):
        # First number should match second to last number, second number should
        # match third to last, etc.
        z = num % x[-(i+2)]
        print(z, num, x[-(i+2)])


x = [1, 3, 5, 7, 9]
fancy_mod(x)
