.DEFAULT_GOAL := build
.PHONY: build wheel install-wheel install-dev clean test

build:
	$(MAKE) -C pgbuild all
	python3 scripts/relocate-native.py

wheel: build
	python setup.py bdist_wheel

install-wheel: wheel
	python -m pip install --force-reinstall dist/*.whl

install-dev: build
	python -m pip install --force-reinstall -e .

clean:
	rm -rf build/ wheelhouse/ dist/ .eggs/
	$(MAKE) -C pgbuild clean

test:
	python -m pytest tests/
