from IPython.terminal.interactiveshell import TerminalInteractiveShell
from pdb import Pdb


class RoboDuckTerminalInteractiveShell(TerminalInteractiveShell):
    """TODO: docs"""

    debugger_cls = Pdb