"""Errors that explain themselves! Or more precisely, errors that are explained
to you by a gpt-esque model. Simply importing this module will change python's
default behavior when it encounters an error.

Quickstart
----------
Importing the errors module automatically enables optional error explanations.
`disable()` reverts to python's regular behavior on errors. `enable()` can be
used to re-enable error explanations or to change settings. For example,
setting auto=True automatically explains all errors rather than asking the user
if they want an explanation (y/n) when an error occurs.
```
from roboduck import errors

data = {'x': 0}
y = data.x

errors.disable()
y = data.x

errors.enable(auto=True)
y = data.x
```
"""
from functools import partial
from IPython import get_ipython
import sys
from traceback import TracebackException
import warnings

from roboduck.debug import DuckDB, CodeCompletionCache
from roboduck.decorators import add_docstring

default_excepthook = sys.excepthook
ipy = get_ipython()


@add_docstring(DuckDB.__init__)
def post_mortem(t=None, Pdb=DuckDB, trace='', prompt_name='debug_stack_trace',
                colordiff=True, **kwargs):
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
    prompt_name: str
        The prompt name that will be passed to our debugger class. Usually
        should leave this as the default. We expect the name to contain
        'debug' and will warn if it doesn't.
    colordiff: bool
        If True, the new code snippet in the exception will print new
        parts in green.
    kwargs: any
        Additional kwargs to pass to debugger class constructor. The docstring
        of the default class is included below for reference.
    """
    if t is None:
        t = sys.exc_info()[2]
        assert t is not None, "post_mortem outside of exception context"
    if 'debug' not in prompt_name:
        warnings.warn(
            f'You passed an unexpected prompt_name ({prompt_name}) to '
            f'post_mortem. Are you sure you didn\'t mean to use '
            f'debug_stack_trace?'
        )
    assert trace, 'Trace passed to post_mortem should be truthy.'

    # This serves almost like a soft assert statement - if user defines some
    # custom debugger class and the question leaks through, gpt should
    # hopefully warn us.
    dummy_question = (
        'This is a fake question to ensure that our ask_language_model '
        'method gets called. Our debugger class should remove this from the '
        'prompt kwargs before calling gpt. If you can read this, can you '
        'indicate that in your response?'
    )
    kwargs['color'] = kwargs.get('color', 'red')
    p = Pdb(prompt_name=prompt_name, **kwargs)
    p.reset()
    p.cmdqueue.insert(0, (dummy_question, trace))
    p.cmdqueue.insert(1, 'q')
    p.interaction(None, t)

    # Make gpt explanation available as part of last error message,
    # accessible via sys.last_value.
    last_value = getattr(sys, 'last_value', None)
    if CodeCompletionCache.last_completion and last_value:
        code_name = 'last_code_diff' if colordiff else 'last_new_code'
        last_value.args = tuple(
            arg if i else f'{arg}\n\n{CodeCompletionCache.last_explanation}'
                          f'\n\n{getattr(CodeCompletionCache, code_name)}'
            for i, arg in enumerate(last_value.args)
        )


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


def excepthook(etype, val, tb, prompt_name='debug_stack_trace',
               auto=False, cls=DuckDB, **kwargs):
    """Replaces sys.excepthook when module is imported. When an error is
    thrown, the user is asked whether they want an explanation of what went
    wrong. If they enter 'y' or 'yes', it will query gpt for help. Unlike
    roboduck.debug.duck(), the user does not need to manually type a
    question, and we don't linger in the debugger - we just write gpt's
    explanation and exit.

    Disable by calling roboduck.errors.disable().

    Parameters are the same as the default sys.excepthook function. Kwargs
    are forwarded to our custom postmortem function.
    """
    sys.last_type, sys.last_value, sys.last_traceback = etype, val, tb
    trace = print_exception(etype, val, tb)
    if not kwargs.get('silent', False):
        print(trace)
    kwargs.update(prompt_name=prompt_name, trace=trace, t=tb, Pdb=cls)
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
        prompt_name (str) - determines what prompt/prompt_name the custom
            debugger uses, e.g. "debug_stack_trace"
        colordiff (bool) - if True, new code snippet will print new parts
            in green.
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
    try:
        # Tried doing `ipy.set_custom_exc((Exception,), None)` as suggested by
        # stackoverflow and chatgpt but it didn't quite restore the default
        # behavior. Manually remove this instead. I'm assuming only one custom
        # exception handler can be assigned for any one exception type and that
        # if we call disable(), we wish to remove the handler for Exception.
        ipy.custom_exceptions = tuple(x for x in ipy.custom_exceptions
                                      if x != Exception)
    except AttributeError:
        pass


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
