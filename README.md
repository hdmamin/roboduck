# roboduck
![roboduck logo](data/images/roboduck_blue.png)

A natural language debugger.

**Documentation**: https://hdmamin.github.io/roboduck/

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
├── notes        # Miscellaneous notes stored as raw text files.
├── notebooks    # Jupyter notebooks for experimentation and exploratory analysis.
├── bin          # Executable scripts to be run from the project root directory.
└── lib          # Python package. Code can be imported in analysis notebooks, py scripts, etc.
```
