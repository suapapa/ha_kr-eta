test:
	uv venv
	uv pip install -r requirements.test.txt
	uv run pytest