from IPython.terminal.interactiveshell import TerminalInteractiveShell
from pdb import Pdb


class RoboDuckTerminalInteractiveShell(TerminalInteractiveShell):

    debugger_cls = Pdb