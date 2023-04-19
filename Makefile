.PHONY: todo nb clean lib pypi readmes

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
	chmod u+x lib/scripts/make_chat_prompt.sh
	lib/scripts/make_chat_prompt.sh
