"""This module allows our roboduck `%duck` magic to work in ipython. Ipython
uses a TerminalInteractiveShell class which makes its debugger_cls attribute
read only. We provide a drop-in replacement that allows our magic class to
set that attribute when necessary. Note that you'd need to start an ipython
session with the command:

```
ipython --TerminalIPythonApp.interactive_shell_class=roboduck.shell.RoboDuckTerminalInteractiveShell
```

for this to work. You'll still need to run `from roboduck import magic` inside
your session to make it avaialble.

Alternatively, you can make it available automatically for all ipython
sessions by adding the following lines to your ipython config (usually found at
~/.ipython/profile_default/ipython_config.py):

```
cfg = get_config()
cfg.TerminalIPythonApp.interactive_shell_class = roboduck.shell.RoboDuckTerminalInteractiveShell
cfg.InteractiveShellApp.exec_lines = ["from roboduck import magic"]
```
"""
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from pdb import Pdb


class RoboDuckTerminalInteractiveShell(TerminalInteractiveShell):
    """TerminalInteractiveShell replacement class whose debugger_cls attribute
    is NOT read-only, thereby allowing our `duck` magic to overwrite it when
    necessary.
    """

    debugger_cls = Pdb
