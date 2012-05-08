all:
	python setup.py --quiet build

test: install
	tweetabs -c data

install: all
	python setup.py install 
