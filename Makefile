.PHONY: clean dist release test

clean:
	rm -rf dist build

dist: clean
	python3 setup.py sdist bdist_wheel

release: test dist twine_check
	python3 -m twine upload dist/*

twine_check:
	twine check dist/*.whl

test:
	pytest -v ./test --capture=no
