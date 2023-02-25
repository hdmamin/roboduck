# Prototyped method to auto ask basic question without requiring user to type
# it. Elegant but probably not the most functional - we don't actually pass the
# stack trace or error to gpt, so it's just inferring what the issue is.
from roboduck.debugger import RoboDuckDB
import sys
import traceback


def my_post_mortem(t=None, Pdb=RoboDuckDB):
    if t is None:
        t = sys.exc_info()[2]
        assert t is not None, "post_mortem outside of exception context"

    p = Pdb()
    p.reset()
    p.cmdqueue.insert(0, 'What caused this error?')
    p.cmdqueue.insert(1, 'q')
    p.interaction(None, t)

def ipy_excepthook(self, etype, evalue, tb, tb_offset):
    """IPython doesn't use sys.excepthook. We have to handle this separately
    and make sure it expects the right arguments.
    """
    return excepthook(etype, evalue, tb)

def excepthook(type_, val, tb):
    """Replaces sys.excepthook when module is imported, which makes us enter
    a debugging session whenever an error is thrown. Disable by calling
    autodebug.disable().
    """
    traceback.print_exception(type_, val, tb)
    my_post_mortem(tb)

get_ipython().set_custom_exc((Exception,), ipy_excepthook)
