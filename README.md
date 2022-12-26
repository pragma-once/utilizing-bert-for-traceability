# Utilizing BERT for requirement-to-code traceability link recovery

Making the most out of BERT for requirements to code traceability using code augmentation, and 3-stage training for issue-method data.

# Data Extraction

Tools to extract issue-commit and issue-method data from GitHub repositories.
Checkout [datasets](https://github.com/pragma-once/tracebert-improved/tree/main/data-extraction#datasets) to get the extracted data.

# Code Augmentation

Java code to apply data augmentation on datasets containing Java methods.

# BERT Train

Code for training and testing the model.

# CODFREL

A Python implementation of another traceability link recovery method, [CODFREL](https://doi.org/10.1016/j.infsof.2019.106235).
This is used for comparison.
