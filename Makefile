.PHONY: clean dist release test

clean:
	rm -rf dist build

dist: clean
	python setup.py sdist bdist_wheel

release: test dist twine_check
	python -m twine upload dist/*

twine_check:
	twine check dist/*.whl

test:
	pytest-3 -v ./test --capture=no
