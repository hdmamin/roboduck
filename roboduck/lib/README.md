# Lib

This folder is for importable python libraries/packages.


---
Start of auto-generated file data.<br/>Last updated: 2023-03-16 19:32:17

<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th>File</th>
      <th>Summary</th>
      <th>Line Count</th>
      <th>Last Modified</th>
      <th>Size</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>__init__.py</td>
      <td>_</td>
      <td>1</td>
      <td>2023-02-02 19:52:40</td>
      <td>21.00 b</td>
    </tr>
    <tr>
      <td>debugger.py</td>
      <td>A conversational debugger and drop-in replacement for pdb. Python's default<br/>interactive debugging session is already a crude conversation with your<br/>program or interpreter, in a sense - this just lets your program communicate to<br/>you more effectively.<br/><br/>Quickstart<br/>----------<br/># Our replacement for python's `breakpoint`.<br/>from roboduck.debugger import duck<br/><br/># Broken version of bubble sort. Notice the duck() call on the second to last<br/># line.<br/>def bubble_sort(nums):<br/>    for i in range(len(nums)):<br/>        for j in range(len(nums)):<br/>            if nums[j] &gt; nums[j + 1]:<br/>                nums[j + 1], nums[j] = nums[j], nums[j + 1]<br/>                duck()<br/>    return nums</td>
      <td>366</td>
      <td>2023-03-16 19:23:21</td>
      <td>15.91 kb</td>
    </tr>
    <tr>
      <td>errors.py</td>
      <td>Errors that explain themselves! Or more precisely, that are explained to you<br/>by a gpt-esque model. Simply importing this module will change python's default<br/>behavior when it encounters an error.<br/><br/>Quickstart<br/>----------<br/># After this import, error explanations are automatically enabled.<br/>from roboduck import errors<br/><br/># Go back to python's regular behavior on errors.<br/>errors.disable()<br/><br/># You can use `enable` to change settings or manually re-enable gpt<br/># explanations. By default, we ask the user if they want an explanation after<br/># each error (y/n). Setting auto=True skips this step and always explains<br/># errors (not recommended in most cases, but it's an option).<br/>errors.enable(auto=True)</td>
      <td>225</td>
      <td>2023-03-16 19:23:21</td>
      <td>9.31 kb</td>
    </tr>
    <tr>
      <td>logging.py</td>
      <td>Logger that attempts to diagnose and propose a solution for any errors it<br/>is asked to log. Unlike our debugger and errors modules, explanations are<br/>not streamed because the intended use case is not focused on live development.<br/><br/>Quickstart<br/>----------<br/>from roboduck import logging<br/><br/>logger = logging.getLogger()</td>
      <td>119</td>
      <td>2023-03-16 19:23:21</td>
      <td>4.83 kb</td>
    </tr>
    <tr>
      <td>magic.py</td>
      <td>GPT-powered rough equivalent of the `%debug` Jupyter magic. After an error<br/>occurs, just run %duck in the next cell to get an explanation. This is very<br/>similar to using the errors module, but is less intrusive - you only call it<br/>when you want an explanation, rather than having to type y/n after each error.<br/>We also provide `paste` mode, which attempts to paste a solution into a new<br/>code cell below, and `interactive` mode, which throws you into a conversational<br/>debugging session (technically closer to the original `%debug` magic<br/>functionality.<br/><br/>Quickstart<br/>----------<br/># cell 1<br/>from roboduck import magic<br/><br/># cell 2<br/>nums = [1, 2, 3]<br/>nums.add(4)<br/><br/># cell 3<br/>%duck</td>
      <td>119</td>
      <td>2023-03-16 19:23:21</td>
      <td>4.71 kb</td>
    </tr>
    <tr>
      <td>shell.py</td>
      <td>This module allows our roboduck `%duck` magic to work in ipython. Ipython<br/>uses a TerminalInteractiveShell class which makes its debugger_cls attribute<br/>read only. We provide a drop-in replacement that allows our magic class to<br/>set that attribute when necessary. Note that you'd need to start an ipython<br/>session with the command:<br/><br/>```<br/>ipython --TerminalIPythonApp.interactive_shell_class=roboduck.shell.RoboDuckTerminalInteractiveShell<br/>```<br/><br/>for this to work. You'll still need to run `from roboduck import magic` inside<br/>your session to make it avaialble.<br/><br/>Alternatively, you can make it available automatically for all ipython<br/>sessions by adding the following lines to your ipython config (usually found at<br/>~/.ipython/profile_default/ipython_config.py):<br/><br/>```<br/>cfg = get_config()<br/>cfg.TerminalIPythonApp.interactive_shell_class = roboduck.shell.RoboDuckTerminalInteractiveShell<br/>cfg.InteractiveShellApp.exec_lines = ["from roboduck import magic"]<br/>```</td>
      <td>34</td>
      <td>2023-02-25 15:42:00</td>
      <td>1.31 kb</td>
    </tr>
    <tr>
      <td>utils.py</td>
      <td>Utility functions used by other roboduck modules.</td>
      <td>307</td>
      <td>2023-03-16 19:23:21</td>
      <td>10.45 kb</td>
    </tr>
  </tbody>
</table>
<br/>End of auto-generated file data. Do not add anything below this.
