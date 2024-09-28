.PHONY: todo nb clean lib pypi readmes docs serve_docs lint

# Convention: add _ between comment sign and TODO to hide an item that you don't want to delete entirely. This will still be findable if you run `ack TODO`.
todo:
	ack -R '# TODO' {bin,lib,notebooks,notes,reports,services} || :

nb:
	cp notebooks/TEMPLATE.ipynb notebooks/nb000-untitled.ipynb

clean:
	cd lib && rm -rf dist
 
lib: clean
	cd lib && python setup.py sdist
 
pypi: lib
	cd lib && twine upload --repository pypi dist/*

readmes:
	htools update_readmes "['bin', 'notebooks', 'lib/roboduck']"

chat_prompt:
	chmod u+x bin/make_chat_prompt.sh
	bin/make_chat_prompt.sh

reinstall:
	pip uninstall -y roboduck && pip install -e ~/roboduck/lib

test:
	# `pytest` does not work. -s flag allows us to see stdout.
	# You can use a command like `python -m pytest -s tests/test_utils.py` to run a single file's tests.
	python -m pytest -s

dev_env:
	chmod u+x bin/make_dev_env.sh && ./bin/make_dev_env.sh

docs:
	cp README.md docs/
	mkdocs build

serve_docs:
	cp README.md docs/
	mkdocs serve

# This updates the gh-pages branch and updates the deployed docs at http://hdmamin.github.io/roboduck.
deploy_docs:
	cp README.md docs/
	mkdocs gh-deploy --force

lint:
	# Only lints docstrings.
	pydocstyle lib/roboduck

typecheck:
	mypy lib/roboduck
