.DEFAULT_GOAL := install

install:
	pip install -r requirements.txt

coverage:
	coverage run -m pytest --doctest-modules && coverage report

test:
	pytest --doctest-modules
