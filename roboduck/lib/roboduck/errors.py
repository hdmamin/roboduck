# Prototyped method to auto ask basic question without requiring user to type
# it. Elegant but probably not the most functional - we don't actually pass the
# stack trace or error to gpt, so it's just inferring what the issue is.
from functools import partial
from IPython import get_ipython
from roboduck.debugger import RoboDuckDB, CodeCompletionCache
import sys
from traceback import TracebackException
import warnings



default_excepthook = sys.excepthook
ipy = get_ipython()


def post_mortem(t=None, Pdb=RoboDuckDB, trace='', dev_mode=False,
                question='What caused this error?', task='debug_stack_trace',
                **kwargs):
    """Drop-in replacement (hence the slightly odd arg order, where trace is
    required but third positionally) for pdb.post_mortem that allows us to get
    both the stack trace AND global/local vars from the program state right
    before an exception occurred.

    Parameters
    ----------
    t: some kind of traceback type?
        A holdover from the default post_mortem class, not actually sure what
        type this is but it doesn't really matter for our use.
    Pdb: type
        Debugger class. Name is capitalized to provide consistent interface
        with default post_mortem function.
    trace: str
        Stack trace formatted as a single string. Required - default value
        just helps us maintain a consistent interface with pdb.post_mortem.
    dev_mode: bool
        If True, print the full gpt prompt before making the query.
    question: str
        The question that gets asked to gpt when an error occurs. Usually just
        leave this as the default. If you want to do more custom/in-depth
        debugging, it's better to use roboduck.debugger.duck() (our
        breakpoint() replacement).
        NOTE: this gets ignored by our RoboDuckDB class if the specified task
        does not accept a question field. debug_stack_trace does not, so this
        is ignored by default.
    task: str
        The prompt name that will be passed to our debugger class. Usually
        should leave this as the default. We expect the name to contain
        'debug' and will warn if it it doesn't.
    kwargs: any
        Additional kwargs to pass to Pdb instantiation.
    """
    if t is None:
        t = sys.exc_info()[2]
        assert t is not None, "post_mortem outside of exception context"
    if 'debug' not in task:
        warnings.warn(f'You passed an unexpected task ({task}) to '
                      f'post_mortem. Are you sure you didn\'t mean to use '
                      f'debug_stack_trace?')
    assert trace, 'Trace passed to post_mortem should be truthy.'

    p = Pdb(task=task, **kwargs)
    p.reset()
    if dev_mode:
        question = f'[dev] {question}'
    p.cmdqueue.insert(0, (question, trace))
    p.cmdqueue.insert(1, 'q')
    p.interaction(None, t)

    # Make gpt explanation available as part of last error message,
    # accessible via sys.last_value.
    # TODO: may need to update the answer parsing code if I change the prompt
    # with chatgpt, i.e. no SOLUTION PART 2.
    last_value = getattr(sys, 'last_value', None)
    if CodeCompletionCache.last_completion and last_value:
        explanation = CodeCompletionCache.last_completion.split(
            'SOLUTION PART 2'
        )[0]
        last_value.args = tuple(arg if i else f'{arg}\n\n{explanation}'
                                for i, arg in enumerate(last_value.args))


def print_exception(etype, value, tb, limit=None, file=None, chain=True):
    """Replacement for traceback.print_exception() that returns the
    whole stack trace as a single string. Used in roboduck's custom excepthook
    to allow us to show the stack trace to gpt. The original function's
    docstring is below:

    Print exception up to 'limit' stack trace entries from 'tb' to 'file'.

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
    if file != sys.stderr:
        with open(file, 'w') as f:
            f.write(trace)
    return trace


def excepthook(etype, val, tb, task='debug_stack_trace',
               auto=False, cls=RoboDuckDB, **kwargs):
    """Replaces sys.excepthook when module is imported. When an error is
    thrown, the user is asked whether they want an explanation of what went
    wrong. If they enter 'y' or 'yes', it will query gpt for help. Unlike
    roboduck.debugger.duck(), the user does not need to manually type a
    question, and we don't linger in the debugger - we just write gpt's
    explanation and exit.

    Disable by calling roboduck.errors.disable().

    Parameters are the same as the default sys.excepthook function.
    """
    sys.last_type, sys.last_value, sys.last_traceback = etype, val, tb
    trace = print_exception(etype, val, tb)
    print(trace)
    kwargs.update(task=task, trace=trace, t=tb, Pdb=cls)
    if auto:
        return post_mortem(**kwargs)
    while True:
        cmd = input('Explain error message? [y/n]\n').lower().strip()
        if cmd in ('y', 'yes'):
            return post_mortem(**kwargs)
        if cmd in ('n', 'no'):
            return
        print('Unrecognized command. Valid choices are "y" or "n".\n')


def enable(**kwargs):
    """Enable conversational debugging mode. This is called automatically on
    module import. However, users may wish to make changes, e.g. set auto=True
    or pass in a custom debugger cls, and this function makes that possible.

    Parameters
    ----------
    kwargs: any
        auto (bool) - if True, automatically have gpt explain every error that
            occurs. Mostly useful for logging in production. You almost
            certainly want to keep this as the default of False for any
            interactive development.
        cls (type) - the debugger class to use.
        task (str) - determines what prompt/task the custom debugger uses, e.g.
            "debug_stack_trace"
        Or any other args that can be passed to our debugger cls.
    """
    hook = partial(excepthook, **kwargs)

    def ipy_excepthook(self, etype, evalue, tb, tb_offset):
        """IPython doesn't use sys.excepthook. We have to handle this case
        separately and make sure it expects the right argument names.
        """
        return hook(etype, evalue, tb)

    # Overwrite default error handling.
    sys.excepthook = hook

    # Only necessary/possible when in ipython.
    try:
        ipy.set_custom_exc((Exception,), ipy_excepthook)
    except AttributeError:
        pass


def disable():
    """Revert to default behavior when exceptions are thrown.
    """
    sys.excepthook = default_excepthook
    # Tried doing `ipy.set_custom_exc((Exception,), None)` as suggested by
    # stackoverflow and chatgpt but it didn't quite restore the default
    # behavior. Manually remove this instead. I'm assuming only one custom
    # exception handler can be assigned for any one exception type and that
    # if we call disable(), we wish to remove the handler for Exception.
    ipy.custom_exceptions = tuple(x for x in ipy.custom_exceptions
                                  if x != Exception)


# stack_trace = partial(print_exception, sys.last_type, sys.last_value,
#                       sys.last_traceback)
def stack_trace():
    # Lets us recover stack trace as string outside of the functions defined
    # above, which generally only execute automatically when exceptions are
    # thrown. Don't just define this as a partial because that requires
    # sys.last_value etc. to be available at import time, which it often isn't.
    try:
        return print_exception(sys.last_type, sys.last_value,
                               sys.last_traceback)
    except AttributeError as e:
        raise RuntimeError('No stack trace available because an error has '
                           'not been thrown.') from e


enable()
