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
# cell 1
from roboduck import magic

# cell 2
nums = [1, 2, 3]
nums.add(4)

# cell 3
%duck
"""

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
    @line_magic
    def duck(self, line=''):
        """Silence warnings for a cell. The -p flag can be used to make the
        change persist, at least until the user changes it again.
        """
        args = parse_argstring(self.duck, line)
        if args.i:
            cls = self.shell.debugger_cls
            try:
                self.shell.debugger_cls = DuckDB
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
            self.shell.InteractiveTB.debugger_cls = DuckDB
            self.shell.debugger(force=True)
            self.shell.debugger_cls = self.shell.InteractiveTB.debugger_cls = cls
        else:
            # Confine this import to this if clause rather than keeping a top
            # level import - importing this module overwrites sys.excepthook
            # which we don't necessarily want in most cases.
            from roboduck import errors
            errors.excepthook(sys.last_type, sys.last_value,
                              sys.last_traceback, auto=True)
            errors.disable()

        # Insert suggested code into next cell.
        if args.p and CodeCompletionCache.last_completion:
            self.shell.set_next_input(CodeCompletionCache.last_new_code,
                                      replace=False)
        CodeCompletionCache.reset()


get_ipython().register_magics(DebugMagic)