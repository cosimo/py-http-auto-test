.PHONY: dist

dist:
	rm -rf dist build
	python setup.py sdist bdist_wheel

release:
	python -m twine upload dist/*

test:
	pytest-3 -v ./spec/test*.yaml --capture=no

.PHONY: test
