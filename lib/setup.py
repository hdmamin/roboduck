import os
import setuptools


def requirements(path='requirements.txt'):
    """Load requirements and return a list of strings."""
    with open(path, 'r') as f:
        deps = [line.strip() for line in f]
    return deps


def version():
    """Get library version from __init__.py.

    Returns
    -------
    str
        E.g. '1.0.0'
    """
    path = os.path.join('roboduck', '__init__.py')
    with open(path, 'r') as f:
        for row in f:
            if not row.startswith('__version__'):
                continue
            return row.split(' = ')[-1].strip('\n').strip("'")


def load_file(name):
    """Load contents of file in the same directory as setup.py and return it as
    a string.

    Parameters
    ----------
    name : str
    """
    path = os.path.join(os.path.dirname(__file__), name)
    with open(path, 'r') as f:
        return f.read()


setuptools.setup(
    name='roboduck',
    version=version(),
    python_requires='>=3.8',
    author='Harrison Mamin',
    author_email='harrisonmamin@gmail.com',
    description='A natural language debugger.',
    long_description=load_file('README.md'),
    long_description_content_type='text/markdown',
    install_requires=requirements(),
    packages=setuptools.find_packages(),
    package_data={
        'roboduck': ['**/*.yaml']
    },
    entry_points={'console_scripts': ['duck=roboduck.cli.cli:run']},
    include_package_data=True,
    project_urls={
        'Documentation': 'https://hdmamin.github.io/roboduck/',
        'Repository': 'https://github.com/hdmamin/roboduck'
    },
    keywords='debugging,llm,language model,dev tools,errors,jupyter magic,'
             'gpt,openai,langchain',
)

