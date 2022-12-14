# Data Extraction

Tools to extract issue-commit and issue-method data from GitHub repositories.

# Datasets

The datasets extracted using the tools can be found in
[releases](https://github.com/pragma-once/tracebert-improved/releases):

Issue-commit:
[Download](https://github.com/pragma-once/tracebert-improved/releases/download/v0.1/extracted-data-issue-code-diff-2022-06-06.zip)

Issue-method:
[Download](https://github.com/pragma-once/tracebert-improved/releases/download/v0.1/extracted-data-issue-code-method-2022-06-08.zip)

There is no `code_tokens` field in the issue-method datasets.
To add this field, you need to use
[add-code-tokens-to-jsonl](https://github.com/pragma-once/tracebert-improved/releases/download/v0.1/add-code-tokens-to-jsonl.jar)
or build and use it from
[source](https://github.com/pragma-once/tracebert-improved/tree/main/data-extraction/data-extraction/add-code-tokens-to-jsonl).

# Guide

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
