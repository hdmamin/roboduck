<div align="center">
<img src="https://raw.githubusercontent.com/hdmamin/roboduck/main/data/images/roboduck_blue_banner.png" alt="roboduck logo">
<p></p>
<a href="https://hdmamin.github.io/roboduck/"><img src="https://img.shields.io/badge/Documentation-Online-blue.svg" alt="Documentation"></a>
<a href="https://badge.fury.io/py/roboduck"><img src="https://badge.fury.io/py/roboduck.svg" alt="PyPI version"></a>
<a href="https://github.com/hdmamin/roboduck/actions/workflows/main.yml"><img src="https://github.com/hdmamin/roboduck/actions/workflows/main.yml/badge.svg" alt="Build Status"></a>
<a href="https://colab.research.google.com/github/hdmamin/roboduck/blob/main/notebooks/quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a>
<img alt="Python Version" src="https://img.shields.io/badge/python-3.8%2B-blue">
<p></p>
</div>

**rubber duck debugging**: a method of debugging code by articulating a problem in spoken or written natural language. The name is a reference to a story in the book The Pragmatic Programmer in which a programmer would carry around a rubber duck and debug their code by forcing themselves to explain it, line-by-line, to the duck. [[1](https://en.wikipedia.org/wiki/Rubber_duck_debugging)]

**robo duck debugging**: a bit like rubber duck debugging, but the duck talks back.

## About

Have you ever wanted to ask your program why it's not working?

Many AI-powered dev tools help you write boilerplate more quickly, but the hardest and most time-consuming part of programming is often the last mile. Roboduck's goal is to help you understand and fix those bugs. It essentially embeds an LLM (large language model) in the Python interpreter, providing drop-in natural language replacements for Python's standard approaches to:  
- debugging  
- error handling  
- logging  

## Quickstart

### Install

```
pip install roboduck
```

### API Key Setup

You need an openai API key to begin using roboduck. Once you have an account ([sign up here](https://platform.openai.com/signup)), you can visit https://platform.openai.com/account/api-keys to retrieve your key. Your simplest option is then to call `roboduck.set_openai_api_key(api_key, update_config_=True)` which essentially does the following: 

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

## Usage Advice

Language models are not infallible. You should not blindly assume that roboduck's code snippets are flawless or that its explanations are a source of unimpeachable truth. But that's kind of the whole reason roboduck is useful - if LLMs were perfectly reliable, humans wouldn't need to write code at all. We could simply generate it, `./deploy.sh`, and call it a day. Maybe we'll get there eventually but in the meantime, I believe LLMs are best viewed as tools to augment human thought. It's ultimately still up to you to assess and make use of what they tell you. 

It comes back to the name of the library. Sure, as a pun it only kind of makes sense, but it's a good mental cue. Conversing with rubber ducks isn't an effective debugging strategy because bath toys are brilliant programmers - the practice just encourages you to hone in on what the problem is, what you understand and what you don't, what would need to be true for your program to function correctly. Roboduck obviously takes a more active role in the conversation, but that mindset is still useful.

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
Start of auto-generated file data.<br/>Last updated: 2023-06-02 21:08:08

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
      <td>17</td>
      <td>2023-06-01 23:26:46</td>
      <td>548.00 b</td>
    </tr>
    <tr>
      <td>config.py</td>
      <td>Allow us to easily read from and write to roboduck's config file.<br/><br/>Roboduck creates a config file at `~/.roboduck/config.yaml`. This currently<br/>supports only two fields:<br/><br/>- `openai_api_key`: See the [Quickstart](https://hdmamin.github.io/roboduck/)<br/>for setup help.<br/><br/>- `model_name` (optional): Roboduck is configured to use gpt-3.5-turbo by<br/>default. This field lets you change that (e.g. to gpt-4). If present in the<br/>config file, this will take priority over any model_name field specified in a<br/>chat template<br/>(e.g. our [default debug prompt template](https://github.com/hdmamin/roboduck/blob/7ff904972921fd3f82b8b9fd862c4ffc7b61aee4/lib/roboduck/prompts/chat/debug.yaml#L2)).<br/>You can view valid options with `roboduck.available_models()`.<br/>You can still override the config default by manually passing a value into a<br/>function, e.g. `duck(model_name='gpt-4-32k')`.<br/><br/>You can manually edit your config file or use a command like<br/>`roboduck.update_config(model_name='gpt-4')`. Passing in a value of None<br/>(e.g. `roboduck.update_config(model_name=None)`) will delete that field from<br/>your config file.</td>
      <td>181</td>
      <td>2023-05-23 22:09:40</td>
      <td>7.41 kb</td>
    </tr>
    <tr>
      <td>debug.py</td>
      <td>A conversational debugger and drop-in replacement for pdb. Python's default<br/>interactive debugging session is already a crude conversation with your<br/>program or interpreter, in a sense - this just lets your program communicate to<br/>you more effectively.<br/><br/>Quickstart<br/>----------<br/>Here's a broken version of bubble sort that places a `duck()` call on the<br/>second to last line where you might normally call `breakpoint()`.<br/><br/>```<br/>from roboduck import duck<br/><br/>def bubble_sort(nums):<br/>    for i in range(len(nums)):<br/>        for j in range(len(nums) - 1):<br/>            if nums[j] &gt; nums[j + 1]:<br/>                nums[j + 1] = nums[j]<br/>                nums[j] = nums[j + 1]<br/>                duck()   # &lt;--------------------------- instead of breakpoint()<br/>    return nums<br/><br/>nums = [3, 1, 9, 2, 1]<br/>bubble_sort(nums)<br/>```</td>
      <td>571</td>
      <td>2023-05-31 00:16:13</td>
      <td>22.98 kb</td>
    </tr>
    <tr>
      <td>decorators.py</td>
      <td>Miscellaneous decorators used throughout the library.</td>
      <td>305</td>
      <td>2023-05-29 15:21:23</td>
      <td>10.86 kb</td>
    </tr>
    <tr>
      <td>errors.py</td>
      <td>Errors that explain themselves! Or more precisely, errors that are explained<br/>to you by a gpt-esque model. Simply importing this module will change python's<br/>default behavior when it encounters an error.<br/><br/>Quickstart<br/>----------<br/>Importing the errors module automatically enables optional error explanations.<br/>`disable()` reverts to python's regular behavior on errors. `enable()` can be<br/>used to re-enable error explanations or to change settings. For example,<br/>setting auto=True automatically explains all errors rather than asking the user<br/>if they want an explanation (y/n) when an error occurs.<br/>```<br/>from roboduck import errors<br/><br/>data = {'x': 0}<br/>y = data.x<br/><br/>errors.disable()<br/>y = data.x<br/><br/>errors.enable(auto=True)<br/>y = data.x<br/>```</td>
      <td>279</td>
      <td>2023-05-29 16:15:02</td>
      <td>11.44 kb</td>
    </tr>
    <tr>
      <td>ipy_utils.py</td>
      <td>Functions related to loading, saving, or otherwise working with ipython<br/>sessions or jupyter notebooks.</td>
      <td>186</td>
      <td>2023-05-24 21:37:48</td>
      <td>5.70 kb</td>
    </tr>
    <tr>
      <td>logging.py</td>
      <td>Logger that attempts to diagnose and propose a solution for any errors it<br/>is asked to log. Unlike our debugger and errors modules, explanations are<br/>not streamed because the intended use case is not focused on live development.<br/><br/>Quickstart<br/>----------<br/>```<br/>from roboduck import logging<br/><br/>logger = logging.getLogger(path='/tmp/log.txt')<br/>data = {'x': 0}<br/>try:<br/>    x = data.x<br/>except Exception as e:<br/>    logger.error(e)<br/>```</td>
      <td>158</td>
      <td>2023-05-29 16:15:02</td>
      <td>6.33 kb</td>
    </tr>
    <tr>
      <td>magic.py</td>
      <td>GPT-powered rough equivalent of the `%debug` Jupyter magic. After an error<br/>occurs, just run %duck in the next cell to get an explanation. This is very<br/>similar to using the errors module, but is less intrusive - you only call it<br/>when you want an explanation, rather than having to type y/n after each error.<br/>We also provide `paste` mode, which attempts to paste a solution into a new<br/>code cell below, and `interactive` mode, which throws you into a conversational<br/>debugging session (technically closer to the original `%debug` magic<br/>functionality.<br/><br/>Quickstart<br/>----------<br/>```<br/># cell 1<br/>from roboduck import magic<br/><br/>nums = [1, 2, 3]<br/>nums.add(4)<br/>```<br/><br/>```<br/># cell 2<br/>%duck<br/>```</td>
      <td>127</td>
      <td>2023-05-30 22:28:43</td>
      <td>5.18 kb</td>
    </tr>
    <tr>
      <td>utils.py</td>
      <td>Utility functions used by other roboduck modules.</td>
      <td>420</td>
      <td>2023-05-27 21:32:29</td>
      <td>15.14 kb</td>
    </tr>
  </tbody>
</table>
<br/>End of auto-generated file data. Do not add anything below this.
