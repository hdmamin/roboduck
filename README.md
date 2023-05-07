|||
|---|---|
| ![roboduck logo](data/images/roboduck_blue_small.png) | <h1>RoboDuck</h1> [![Documentation](https://img.shields.io/badge/Documentation-Online-blue.svg)](https://hdmamin.github.io/roboduck/) [![PyPI version](https://badge.fury.io/py/roboduck.svg)](https://badge.fury.io/py/roboduck) [![Build Status](https://github.com/hdmamin/roboduck/actions/workflows/main.yml/badge.svg)](https://github.com/hdmamin/roboduck/actions/workflows/main.yml) |


*rubber duck debugging*: a method of debugging code by articulating a problem in spoken or written natural language. The name is a reference to a story in the book The Pragmatic Programmer in which a programmer would carry around a rubber duck and debug their code by forcing themselves to explain it, line-by-line, to the duck. [[1](https://en.wikipedia.org/wiki/Rubber_duck_debugging)]

*robo duck debugging*: like rubber duck debugging, but the duck talks back.

## About

Copilot takes your programs from 0 to 50; RoboDuck is designed to get you from 90 to 100. It essentially embeds an LLM (large language model) in the Python interpreter, providing drop-in natural language replacements for Python's standard approaches to:
- debugging  
- error handling  
- logging  

## Quickstart

# TODO add code snippets and gifs

### API Key Setup

You need an openai API key to begin using roboduck. Once you have an account ([sign up here](https://platform.openai.com/signup)), you can visit https://platform.openai.com/account/api-keys to retrieve your key. Your simplest option is to store it in a text file at `~/.openai`. Alternatively, you can call `roboduck.set_openai_api_key(api_key)` or manually set `os.environ['OPENAI_API_KEY'] = api_key`.

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
├── data         # Raw and processed data. Actual files are excluded from github.
├── notes        # Miscellaneous developer notes stored as text files.
├── notebooks    # Jupyter notebooks for experimentation and exploratory analysis.
├── bin          # Executable scripts to be run from the project root directory.
└── lib          # Python package. Code can be imported in analysis notebooks, py scripts, etc.
```
