PY3=python3
PIP3=pip3

.PHONY: build install uninstall reinstall check clean cleanall

build:
	$(PY3) setup.py bdist_wheel

install: build
	$(PIP3) install --user "$(shell ls dist/kedixa-*.whl | sort | tail -1)"

uninstall:
	$(PIP3) uninstall -y kedixa

reinstall: uninstall install

check:
	cd test && pytest .

clean:
	rm -rf build kedixa.egg-info

cleanall: clean
	rm -rf dist
