"""Jupyter magics."""

from IPython import get_ipython
from IPython.core.magic import line_magic, magics_class, Magics
from IPython.core.magic_arguments import argument, magic_arguments, \
    parse_argstring
import sys

from roboduck.debugger import RoboDuckDB, CodeCompletionCache


@magics_class
class DebugMagic(Magics):
    """Enter a conversational debugging session after an error is thrown by a
    jupyter notebook code cell.

    Examples
    --------
    After a cell execution throws an error, enter this in the next cell to
    enter an interactive conversational debugging session:

    %duck

    If the -i flag is present, we will try to Insert a new code cell upon
    exiting the debugger containing the fixed code snippet.

    %duck -i
    """

    @magic_arguments()
    @argument('-i', action='store_true',
              help='Boolean flag: if provided, INSERT a new code cell with '
                   'the suggested code fix.')
    @argument('-a', action='store_true',
              help='Boolean flag: if provided, use AUTO mode. Rather than '
                   'starting an interactive debugging session and requiring '
                   'the user to enter a question, auto mode simply asks gpt '
                   'what caused the error that just occurred.')
    @line_magic
    def duck(self, line=''):
        """Silence warnings for a cell. The -p flag can be used to make the
        change persist, at least until the user changes it again.
        """
        args = parse_argstring(self.duck, line)
        # TODO: auto mode currently doesn't support insert mode. If everything
        # looks good with auto mode and I decide to keep it, should implement
        # that.
        if args.a:
            # Confine this import to this if clause rather than keeping a top
            # level import - importing this module overwrites sys.excepthook
            # which we don't necessarily want in most cases.
            from roboduck import errors
            errors.excepthook(sys.last_type, sys.last_value,
                              sys.last_traceback, require_confirmation=False)
            errors.disable()
            return
        cls = self.shell.debugger_cls
        try:
            self.shell.debugger_cls = RoboDuckDB
        except AttributeError:
            print(
                'Roboduck is unavailable in your current ipython session. To '
                'use it, start a new session with the command:\n\nipython '
                '--TerminalIPythonApp.interactive_shell_class=roboduck.shell.'
                'RoboDuckTerminalInteractiveShell\n\n(You will also need to '
                'run `from roboduck import magic` in the session to make the '
                'magic available.) To make it available automatically for all '
                'ipython sessions by default, add the following lines to '
                'your ipython config (usually found at '
                '~/.ipython/profile_default/ipython_config.py):\n\n'
                'cfg = get_config()\ncfg.TerminalIPythonApp.interactive_'
                'shell_class = roboduck.shell.RoboDuckTerminalInteractiveShell'
                '\ncfg.InteractiveShellApp.exec_lines = '
                '["from roboduck import magic"]'
            )
            return
        self.shell.InteractiveTB.debugger_cls = RoboDuckDB
        self.shell.debugger(force=True)
        # Insert suggested code into next cell.
        if args.i and CodeCompletionCache.last_completion:
            *_, code_snippet = CodeCompletionCache.last_completion.split(
                'SOLUTION PART 2:'
            )
            self.shell.set_next_input(code_snippet.lstrip('\n'),
                                      replace=False)
        CodeCompletionCache.last_completion = ''
        self.shell.debugger_cls = self.shell.InteractiveTB.debugger_cls = cls


get_ipython().register_magics(DebugMagic)