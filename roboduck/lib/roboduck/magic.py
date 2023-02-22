"""Jupyter magics."""

from IPython.core.magic import line_magic, magics_class, Magics
from IPython.core.magic_arguments import argument, magic_arguments, \
    parse_argstring

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
    @line_magic
    def duck(self, line=''):
        """Silence warnings for a cell. The -p flag can be used to make the
        change persist, at least until the user changes it again.
        """
        args = parse_argstring(self.duck, line)
        cls = self.shell.debugger_cls
        # TODO: this raises AttributeError in ipython.
        try:
            self.shell.debugger_cls = RoboDuckDB
        except AttributeError:
            print('Roboduck is unavailable in your current ipython session. '
                  'To use it, start a new session with the command:\n\n'
                  'ipython --TerminalIPythonApp.interactive_shell_class='
                  'roboduck.shell.RoboDuckTerminalInteractiveShell')
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