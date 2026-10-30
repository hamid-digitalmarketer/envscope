.PHONY: test demo install clean

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

demo:
	cd examples && PYTHONPATH=../src python -m envscope check --example .env.example --env .env --schema envscope.json; true

install:
	python -m pip install -e .

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info
