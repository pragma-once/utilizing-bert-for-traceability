# Data Extraction

Tools to extract issue-commit and issue-method data from GitHub repositories.

Steps to produce issue-commit data:

1. `retrieve_issues.py` (needs `github_token.py` fields)
2. `retrieve_code.py`
3. `process_issues.py`
4. `extract_data.py` with its `CODE_CONTENT` variable set to `DIFF_LINES_AS_CODE`

Steps to produce issue-method data:

1. `retrieve_issues.py` (needs `github_token.py` fields)
2. `retrieve_code.py`
3. `process_issues.py`
4. `extract_data.py` with its `CODE_CONTENT` variable set to `METHODS_AS_CODE`
5. `extract-data-java-methods`

The `clib/` directory inside `data-extraction/` contains the C++ implementation of the diff algorithm.
You can remove the library file inside it to use the Python implementation in `utils.py`.
