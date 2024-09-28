"""GPT-powered rough equivalent of the `%debug` Jupyter magic. After an error
occurs, just run %duck in the next cell to get an explanation. This is very
similar to using the errors module, but is less intrusive - you only call it
when you want an explanation, rather than having to type y/n after each error.
We also provide `paste` mode, which attempts to paste a solution into a new
code cell below, and `interactive` mode, which throws you into a conversational
debugging session (technically closer to the original `%debug` magic
functionality.

Quickstart
----------
```
# cell 1
from roboduck import magic

nums = [1, 2, 3]
nums.add(4)
```

```
# cell 2
%duck
```
"""

from IPython import get_ipython
from IPython.core.magic import line_magic, magics_class, Magics
from IPython.core.magic_arguments import argument, magic_arguments, \
    parse_argstring
import sys
import warnings

from roboduck.debug import CodeCompletionCache
from roboduck.ipy_utils import is_colab


@magics_class
class DebugMagic(Magics):
    """Enter a conversational debugging session after an error is thrown by a
    jupyter notebook code cell.

    Examples
    --------
    After a cell execution throws an error, enter this in the next cell to
    get an explanation of what caused the error and how to fix it:

    %duck

    To instead enter an Interactive conversational debugging session:

    %duck -i

    If the -p flag is present, we will try to Paste a solution into a new
    code cell upon exiting the debugger containing the fixed code snippet.

    %duck -p

    Flags can be combined:

    %duck -ip
    """

    @magic_arguments()
    @argument('-p', action='store_true',
              help='Boolean flag: if provided, try to PASTE a solution into a '
                   'new code cell below. If you also choose to use '
                   'interactive mode and receive multiple replies containing '
                   'code snippets, the last snippet to be generated will be '
                   'the one that is pasted in (we make the assumption that '
                   'users will prompt for increasingly correct code rather '
                   'than the reverse).')
    @argument('-i', action='store_true',
              help='Boolean flag: if provided, use INTERACTIVE mode. Start a '
                   'conversational debugger session and allow the user to ask '
                   'custom questions, just as they would if using '
                   'roboduck.debug.duck(). The default mode, meanwhile, '
                   'simply asks gpt what caused the error that just '
                   'occurred and then exits, rather than lingering in a '
                   'debugger session.')
    @argument('--prompt', type=str, default=None)
    @line_magic
    def duck(self, line: str = ''):
        """Silence warnings for a cell. The -p flag can be used to make the
        change persist, at least until the user changes it again.

        Developer note: later found a needs_local_scope decorator
        https://ipython.readthedocs.io/en/stable/config/custommagics.html#\
            accessing-user-namespace-and-local-scope
        that might let us load state from ipython in a a more reliable way.
        Not certain this would be an improvement, and major refactor might be
        needed to make this work, but it's something to keep in mind.
        """
        args = parse_argstring(self.duck, line)
        if args.prompt:
            warnings.warn('Support for custom prompts is somewhat limited '
                          'at the moment - your prompt must use the default '
                          'parse_func (roboduck.utils.parse_completion).')
        if args.p and is_colab(self.shell):
            warnings.warn('Paste mode is unavailable in google colab, which '
                          'you appear to be using. Ignoring -p flag.')
        try:
            # Confine this import to this method rather than keeping a top
            # level import because importing this module overwrites
            # sys.excepthook which we don't necessarily want when
            # importing this module.
            # Note that this uses the `debug_stack_trace` prompt by default.
            # This does NOT include a user question param in the contextful
            # prompt, but in this setting we only use that method once (for our
            # automatic question) because excepthook transports us to one
            # step before the error. The user can ask followup questions but
            # the code state will not progress because we can't step through
            # any further, and thus the contextless method (which does include
            # a user question) is used from that point forward.
            # Color should be specified because errors module uses red
            # by default (whereas debug module uses green).
            from roboduck import errors
            kwargs = {'auto': True, 'interactive': args.i, 'color': 'green'}
            if args.prompt:
                kwargs['prompt'] = args.prompt
            errors.excepthook(sys.last_type, sys.last_value,  # type: ignore
                              sys.last_traceback, **kwargs)
        except Exception as e:
            pass
        finally:
            errors.disable()

        # Insert suggested code into next cell.
        if args.p and CodeCompletionCache.get('last_completion'):
            self.shell.set_next_input(CodeCompletionCache.get('last_new_code'),
                                      replace=False)
        CodeCompletionCache.reset_class_vars()


get_ipython().register_magics(DebugMagic)
