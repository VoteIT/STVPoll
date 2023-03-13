.DEFAULT_GOAL := install

install:
	pip install -r requirements.txt

coverage:
	coverage run -m unittest stvpoll.tests stvpoll_testing.tests && coverage report

test:
	python -m unittest stvpoll.tests stvpoll_testing.tests --failfast
