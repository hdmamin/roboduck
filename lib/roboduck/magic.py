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

from functools import partial
from IPython import get_ipython
from IPython.core.magic import line_magic, magics_class, Magics
from IPython.core.magic_arguments import argument, magic_arguments, \
    parse_argstring
import sys
import warnings

from roboduck.debug import DuckDB, CodeCompletionCache


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
                   'new code cell below.')
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
    def duck(self, line=''):
        """Silence warnings for a cell. The -p flag can be used to make the
        change persist, at least until the user changes it again.
        """
        args = parse_argstring(self.duck, line)
        if args.prompt:
            warnings.warn('Support for custom prompts is somewhat limited - '
                          'your prompt must use the default parse_func '
                          '(roboduck.utils.parse_completion).')
        if args.i:
            old_cls = self.shell.debugger_cls
            if args.prompt:
                new_cls = partial(DuckDB, prompt=args.prompt)
            else:
                new_cls = DuckDB
            try:
                self.shell.debugger_cls = new_cls
            except AttributeError:
                print(
                    'Roboduck is unavailable in your current ipython session. '
                    'To use it, start a new session with the command:\n\n'
                    'ipython --TerminalIPythonApp.interactive_shell_class='
                    'roboduck.shell.RoboDuckTerminalInteractiveShell\n\n'
                    '(You will also need to run `from roboduck import '
                    'magic` in the session to make the magic available.) To '
                    'make it available automatically for all '
                    'ipython sessions by default, add the following lines to '
                    'your ipython config (usually found at '
                    '~/.ipython/profile_default/ipython_config.py):\n\n'
                    'cfg = get_config()\ncfg.TerminalIPythonApp.interactive_'
                    'shell_class = roboduck.shell.'
                    'RoboDuckTerminalInteractiveShell'
                    '\ncfg.InteractiveShellApp.exec_lines = '
                    '["from roboduck import magic"]'
                )
                return
            self.shell.InteractiveTB.debugger_cls = new_cls
            self.shell.debugger(force=True)
            self.shell.debugger_cls = self.shell.InteractiveTB.debugger_cls = old_cls
        else:
            # Confine this import to this if clause rather than keeping a top
            # level import - importing this module overwrites sys.excepthook
            # which we don't necessarily want in most cases.
            # Note that this uses the `debug_stack_trace` prompt by default
            # whereas interactive mode uses `debug` by default.
            # UPDATE: we could probably use excepthook for both cases
            # (args.i = True or False) now that
            # I added interactive support in the errors module. However,
            # everything is working nicely now and I don't see a compelling
            # reason to change things at the moment.
            from roboduck import errors
            kwargs = {'auto': True, 'color': 'green'}
            if args.prompt:
                kwargs['prompt'] = args.prompt
            errors.excepthook(sys.last_type, sys.last_value,
                              sys.last_traceback, **kwargs)
            errors.disable()

        # Insert suggested code into next cell.
        if args.p and CodeCompletionCache.last_completion:
            self.shell.set_next_input(CodeCompletionCache.last_new_code,
                                      replace=False)
        CodeCompletionCache.reset_class_vars()


get_ipython().register_magics(DebugMagic)