# BERT Train

Code for training and testing based on [TraceBERT](https://github.com/jinfenglin/TraceBERT).
TraceBERT's original code can be found in bert-train/TraceBERT-master/ which is imported in
the scripts in bert-train/ to slightly modify TraceBERT and use it for Java doc-method,
issue-commit and issue-method links.

# Scripts

Some of the scripts are described below.

## Intermediate

Intermediate training using [CodeSearchNet](https://github.com/github/CodeSearchNet) Java data.

Files: `intermediate-train.py`, `intermediate-eval.py`

## Intermediate 2

This is for 3-stage training.
The issue-method data is used and it's done after the first intermediate training
(loading the first intermediate model).

Files: `intermediate-2-train.py` (`finetuning-eval.py` used for evaluation because of the same data format)

## Fine tuning

The final training step with separate "-codelines" variants for issue-commit data.
Supports issue-method data without "-codelines" postfix.

Files: `finetuning-train.py`, `finetuning-eval.py`, `finetuning-train-codelines.py`, `finetuning-eval-codelines.py`


## CodeSearchNet test data filter

Used to remove similar rows for better evaluation.
CodeSearchNet Java test data contains a lot of very similar rows that alters the evaluation results
by assuming some true positives as false positives.
This problem is not present in the validation data.

File: `filter-intermediate-test-data.py`

## Data organization

Scripts used to organize fine tuning data.

Folder: `data-organization/` inside `bert-train/`
