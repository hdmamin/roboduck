from IPython.terminal.interactiveshell import TerminalInteractiveShell
from pdb import Pdb


class RoboDuckTerminalInteractiveShell(TerminalInteractiveShell):
    """Allows roboduck magic to work in ipython. Ipython uses
    TerminalInteractiveShell which makes debugger_cls attribute read only.
    We overwrite it here so that our magic class can set it to our desired
    class when requested.
    """

    debugger_cls = Pdb