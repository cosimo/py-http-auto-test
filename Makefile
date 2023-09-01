.PHONY: clean dist release test

clean:
	rm -rf dist build

dist: clean
	python setup.py sdist bdist_wheel

release: test dist
	python -m twine upload dist/*

test:
	pytest-3 -v ./test --capture=no
