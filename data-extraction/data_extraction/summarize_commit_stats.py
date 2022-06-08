"""
To summarize commit stats generated from extract_commit_stats.py.
"""

import pandas
import sys

percentiles = [
    0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90,
    0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99
]

def summarize_commit_stats(stats_csv_path_path: str):
    data = pandas.read_csv(stats_csv_path_path)
    print("Commit files count statistics:")
    print("Mean: " + str(data["files_count"].mean()))
    print("Median: " + str(data["files_count"].median()))
    for p in percentiles:
        print(str(p * 100) + "% Percentile: " + str(data["files_count"].quantile(p)))

def main():
    if len(sys.argv) != 2:
        print("Use: python summarize_commit_stats.py stats-csv-file-path")
        exit()
    summarize_commit_stats(sys.argv[1])

if __name__ == "__main__":
    main()
