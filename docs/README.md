<div align="center">
<img src="data/images/roboduck_blue_banner.png" alt="roboduck logo">
<p></p>
<a href="https://hdmamin.github.io/roboduck/"><img src="https://img.shields.io/badge/Documentation-Online-blue.svg" alt="Documentation"></a>
<a href="https://badge.fury.io/py/roboduck"><img src="https://badge.fury.io/py/roboduck.svg" alt="PyPI version"></a>
<a href="https://github.com/hdmamin/roboduck/actions/workflows/main.yml"><img src="https://github.com/hdmamin/roboduck/actions/workflows/main.yml/badge.svg" alt="Build Status"></a>
<a href="https://colab.research.google.com/github/hdmamin/roboduck/blob/main/notebooks/quickstart.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"></a>
<a href="https://github.com/hdmamin/roboduck"><img src="https://img.shields.io/badge/source-code-blue.svg" alt="Source Code"></a>
<img alt="Python Version" src="https://img.shields.io/badge/python-3.8%2B-blue">
<p></p>
</div>

**rubber duck debugging**: a method of debugging code by articulating a problem in spoken or written natural language. The name is a reference to a story in the book The Pragmatic Programmer in which a programmer would carry around a rubber duck and debug their code by forcing themselves to explain it, line-by-line, to the duck. [[1](https://en.wikipedia.org/wiki/Rubber_duck_debugging)]

**robo duck debugging**: a bit like rubber duck debugging, but the duck talks back.

![errors demo](data/images/errors.gif)

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

You need an openai API key to begin using roboduck. Once you have an account ([sign up here](https://platform.openai.com/signup)), you can visit https://platform.openai.com/account/api-keys to retrieve your key. Your simplest option is then to call `roboduck.set_openai_api_key(api_key, update_config=True)` which essentially does the following: 

```bash
mkdir ~/.roboduck
echo "openai_api_key: your_api_key" > ~/.roboduck/config.yaml
```

Manually setting an OPENAI_API_KEY environment variable also works.

Roboduck does not store your API key or collect any usage data.

### Debugger

![debug demo](data/images/debug.gif)

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

![jupyter magic demo](data/images/magic.gif)

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

### Repo Structure
```
roboduck/
├── lib          # Python package source code
├── bin          # Executable scripts to be run from the project root directory.
├── docs         # Markdown templates that mkdocs uses to build automatic documentation.
├── site         # The autogenerated content that makes up our documentation, deployed with github pages.
├── .github      # Build that executes when pushing or merging to main.
├── tests        # Pytest unit tests.
└── data         # Contains images for our README. Used locally to store other miscellaneous files that are excluded from github.
```
