<p align="center">
<img src="https://raw.githubusercontent.com/hdmamin/roboduck/main/data/images/roboduck_blue_banner.png" alt="roboduck logo">
<p></p>
<a href="https://hdmamin.github.io/roboduck/"><img src="https://img.shields.io/badge/Documentation-Online-blue.svg" alt="Documentation"></a>
<a href="https://badge.fury.io/py/roboduck"><img src="https://badge.fury.io/py/roboduck.svg" alt="PyPI version"></a>
<a href="https://github.com/hdmamin/roboduck/actions/workflows/main.yml"><img src="https://github.com/hdmamin/roboduck/actions/workflows/main.yml/badge.svg" alt="Build Status"></a>
<a href="https://colab.research.google.com/github/hdmamin/roboduck/blob/main/notebooks/quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a>
<p></p>
</p>

**rubber duck debugging**: a method of debugging code by articulating a problem in spoken or written natural language. The name is a reference to a story in the book The Pragmatic Programmer in which a programmer would carry around a rubber duck and debug their code by forcing themselves to explain it, line-by-line, to the duck. [[1](https://en.wikipedia.org/wiki/Rubber_duck_debugging)]

**robo duck debugging**: a bit like rubber duck debugging, but the duck talks back.

## About

Many AI-powered dev tools help you write boilerplate more quickly, but the hardest and most time-consuming part of programming is often the last mile. Roboduck's goal is to help you understand and fix those bugs. It essentially embeds an LLM (large language model) in the Python interpreter, providing drop-in natural language replacements for Python's standard approaches to:  
- debugging  
- error handling  
- logging  

## Quickstart

# TODO add gifs


### Install

```
pip install roboduck
```

### API Key Setup

You need an openai API key to begin using roboduck. Once you have an account ([sign up here](https://platform.openai.com/signup)), you can visit https://platform.openai.com/account/api-keys to retrieve your key. Your simplest option is then to call `roboduck.set_openai_api_key(api_key, update_config=True)` which essentially does the following: 

```bash
mkdir ~/.roboduck
echo "openai_api_key: your_api_key" > ~/.roboduck/config.yaml
```

Manually setting an OPENAI_API_KEY environment variable also works.

Roboduck does not store your API key or collect any usage data.

### Debugger

We provide a natural language equivalent of python's built-in `breakpoint` function. Once you're in an interactive session, you can use the standard pdb commands to navigate your code (cmd+f "debugger commands" [here](https://docs.python.org/3/library/pdb.html). TLDR: type `n` to execute the next line, a variable name to view its current value, or `q` to quit the debugging session). However, you can also type a question like "Why do we get an index error when j changes from 3 to 4?" or "Why does nums have three 9s in it when the input list only had one?". Concretely, any time you type something including a question mark, an LLM will try to answer. This is not just performing static analysis - the LLM can access information about the current state of your program.

```
from roboduck import duck

def bubble_sort(nums):
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[j] > nums[j + 1]:
                nums[j + 1] = nums[j]
                nums[j] = nums[j + 1]
                duck()   # <--------------------------- instead of breakpoint()
    return nums

nums = [3, 1, 9, 2, 1]
bubble_sort(nums)
```

### Errors

Roboduck is also good at explaining error messages.  Importing the errors module automatically enables *optional* error explanations. `errors.disable()` reverts to python's regular behavior on errors. `errors.enable()` can be used to re-enable error explanations or to change settings. For example, setting auto=True automatically explains all errors rather than asking the user if they want an explanation (y/n) when an error occurs (this is probably excessive for most use cases, but you're free to do it).

```
from roboduck import errors

data = {'x': 0}
y = data.x

errors.disable()
y = data.x

errors.enable(auto=True)
y = data.x
```

### Jupyter Magic

Jupyter provides a `%debug` magic that can be used after an error occurs to enter a postmortem debugging session. Roboduck's `%duck` magic works similarly, but with all of our debugging module's conversational capabilities:

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

### Logging

Roboduck also provides a logger that can write to stdout and/or a file. Whenever you log an Exception object, an LLM will try to diagnose and suggest a fix for the problem. (Unlike the debug module, the logger does not type responses live because we assume logs will typically be viewed after the fact.)

```
from roboduck import logging

logger = logging.getLogger(path='/tmp/log.txt')
data = {'x': 0}
try:
    x = data.x
except Exception as e:
    logger.error(e)
```

### CLI

You can also run a python script with error explanations enabled:

```bash
duck my_script.py
```

Run `duck --help` for more info.

## Contributing

To create a virtual environment and install relevant packages:
```
make dev_env
```

To run unit tests:
```
make test
```

To rebuild the docs locally:
```
make docs
```

---
Start of auto-generated file data.<br/>Last updated: 2023-04-23 20:52:09

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
      <td>5</td>
      <td>2023-04-16 21:46:51</td>
      <td>142.00 b</td>
    </tr>
    <tr>
      <td>debug.py</td>
      <td>A conversational debugger and drop-in replacement for pdb. Python's default<br/>interactive debugging session is already a crude conversation with your<br/>program or interpreter, in a sense - this just lets your program communicate to<br/>you more effectively.<br/><br/>Quickstart<br/>----------<br/># Our replacement for python's `breakpoint`.<br/>from roboduck.debug import duck<br/><br/># Broken version of bubble sort. Notice the duck() call on the second to last<br/># line.<br/>def bubble_sort(nums):<br/>    for i in range(len(nums)):<br/>        for j in range(len(nums)):<br/>            if nums[j] &gt; nums[j + 1]:<br/>                nums[j + 1], nums[j] = nums[j], nums[j + 1]<br/>                duck()<br/>    return nums</td>
      <td>424</td>
      <td>2023-04-16 21:52:28</td>
      <td>18.17 kb</td>
    </tr>
    <tr>
      <td>errors.py</td>
      <td>Errors that explain themselves! Or more precisely, that are explained to you<br/>by a gpt-esque model. Simply importing this module will change python's default<br/>behavior when it encounters an error.<br/><br/>Quickstart<br/>----------<br/># After this import, error explanations are automatically enabled.<br/>from roboduck import errors<br/><br/># Go back to python's regular behavior on errors.<br/>errors.disable()<br/><br/># You can use `enable` to change settings or manually re-enable gpt<br/># explanations. By default, we ask the user if they want an explanation after<br/># each error (y/n). Setting auto=True skips this step and always explains<br/># errors (not recommended in most cases, but it's an option).<br/>errors.enable(auto=True)</td>
      <td>225</td>
      <td>2023-04-12 21:48:03</td>
      <td>9.27 kb</td>
    </tr>
    <tr>
      <td>logging.py</td>
      <td>Logger that attempts to diagnose and propose a solution for any errors it<br/>is asked to log. Unlike our debugger and errors modules, explanations are<br/>not streamed because the intended use case is not focused on live development.<br/><br/>Quickstart<br/>----------<br/>from roboduck import logging<br/><br/>logger = logging.getLogger()</td>
      <td>118</td>
      <td>2023-04-14 21:55:16</td>
      <td>4.75 kb</td>
    </tr>
    <tr>
      <td>magic.py</td>
      <td>GPT-powered rough equivalent of the `%debug` Jupyter magic. After an error<br/>occurs, just run %duck in the next cell to get an explanation. This is very<br/>similar to using the errors module, but is less intrusive - you only call it<br/>when you want an explanation, rather than having to type y/n after each error.<br/>We also provide `paste` mode, which attempts to paste a solution into a new<br/>code cell below, and `interactive` mode, which throws you into a conversational<br/>debugging session (technically closer to the original `%debug` magic<br/>functionality.<br/><br/>Quickstart<br/>----------<br/># cell 1<br/>from roboduck import magic<br/><br/># cell 2<br/>nums = [1, 2, 3]<br/>nums.add(4)<br/><br/># cell 3<br/>%duck</td>
      <td>134</td>
      <td>2023-04-13 22:05:19</td>
      <td>5.46 kb</td>
    </tr>
    <tr>
      <td>shell.py</td>
      <td>This module allows our roboduck `%duck` magic to work in ipython. Ipython<br/>uses a TerminalInteractiveShell class which makes its debugger_cls attribute<br/>read only. We provide a drop-in replacement that allows our magic class to<br/>set that attribute when necessary. Note that you'd need to start an ipython<br/>session with the command:<br/><br/>```<br/>ipython --TerminalIPythonApp.interactive_shell_class=roboduck.shell.RoboDuckTerminalInteractiveShell<br/>```<br/><br/>for this to work. You'll still need to run `from roboduck import magic` inside<br/>your session to make it avaialble.<br/><br/>Alternatively, you can make it available automatically for all ipython<br/>sessions by adding the following lines to your ipython config (usually found at<br/>~/.ipython/profile_default/ipython_config.py):<br/><br/>```<br/>cfg = get_config()<br/>cfg.TerminalIPythonApp.interactive_shell_class = roboduck.shell.RoboDuckTerminalInteractiveShell<br/>cfg.InteractiveShellApp.exec_lines = ["from roboduck import magic"]<br/>```</td>
      <td>34</td>
      <td>2023-03-20 21:20:45</td>
      <td>1.31 kb</td>
    </tr>
    <tr>
      <td>utils.py</td>
      <td>Utility functions used by other roboduck modules.</td>
      <td>599</td>
      <td>2023-04-21 23:15:17</td>
      <td>21.12 kb</td>
    </tr>
  </tbody>
</table>
<br/>End of auto-generated file data. Do not add anything below this.
