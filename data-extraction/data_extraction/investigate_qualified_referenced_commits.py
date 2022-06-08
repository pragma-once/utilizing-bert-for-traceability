"""
To get the number of referenced commits.
"""

import ast
import git
import os
import pandas
import sys
import utils

"""
MUST be lower case.
"""
LABEL_WORDS_TO_AVOID = [
    "bug",
    "dependency", "dependencies"
]

MIN_CODE_LINES_IN_A_COMMIT = 6
# Commits with more files are ignored.
MAX_FILES_IN_A_COMMIT = 10

COUNT_REMOVED_FILES_LINES = True
COUNT_MODIFIED_FILES_REMOVED_LINES = True

TEST_MODE = False
TEST_MODE_FILES_COUNT = 2

def extract_large_commit_diffs(input_issues_dir: str, input_code_dir: str, output_dir: str):
    qualified_non_duplicate_referenced_commits_count = []
    TEST_processed_files_count = 0
    for input_file_name in os.listdir(input_issues_dir):
        input_file_path = os.path.join(input_issues_dir, input_file_name)
        if os.path.isfile(input_file_path) and input_file_path.endswith(".csv"):
            repo_name = utils.discover_repo_address_from_issue_data(input_file_path, input_file_name)
            if repo_name is None:
                print("Could not find out the repo address of '" + input_file_name + "', skipping...")
                continue
            try:
                repo = git.Repo(os.path.join(input_code_dir, repo_name.replace('/', '_')))
            except:
                print(
                    "Could not open repo '"
                    + os.path.join(input_code_dir, repo_name.replace('/', '_'))
                    + "'. retrieve_code.py must clone repositories before running this script. Skipping this file..."
                )
                continue
            if TEST_MODE:
                if TEST_processed_files_count >= TEST_MODE_FILES_COUNT:
                    break
                TEST_processed_files_count += 1
            print("Processing " + repo_name +  " (" + input_file_name + ")...")
            data = pandas.read_csv(input_file_path)

            def count_commit_lines(diff: utils.CommitDiff):
                count = 0
                for item in diff.added_files:
                    # Doesn't count empty lines
                    count += len([1 for line in item.text.splitlines() if len(line.strip()) != 0])
                if COUNT_REMOVED_FILES_LINES:
                    for item in diff.removed_files:
                        count += len([1 for line in item.text.splitlines() if len(line.strip()) != 0])
                for item in diff.modified_files:
                    if item.new_file_info.mime_type == "text/x-java-source":
                        # Doesn't count empty lines
                        count += len([1 for line in item.added_lines if len(line.line_text.strip()) != 0])
                    if COUNT_MODIFIED_FILES_REMOVED_LINES and item.old_file_info.mime_type == "text/x-java-source":
                        count += len([1 for line in item.removed_lines if len(line.line_text.strip()) != 0])
                return count

            def diff_line_count_filter(diff: utils.CommitDiff):
                return count_commit_lines(diff) >= MIN_CODE_LINES_IN_A_COMMIT

            for row in data.iterrows():
                x = row[1]
                labels = ast.literal_eval(x["labels"])
                for label in labels:
                    if any(
                                word in label.lower()
                                    for word in LABEL_WORDS_TO_AVOID
                            ):
                        continue

                referenced_commits = {}
                detailed_visited_commits: list[utils.CommitDiff] = []
                def operation(issue_row, commit_id, is_referenced_commit = False):
                    try:
                        commit = repo.commit(commit_id)
                    except:
                        return
                    if len([f for f in commit.stats.files if f.endswith(".java")]) > MAX_FILES_IN_A_COMMIT:
                        return
                    diff = utils.CommitDiff(commit, "text/x-java-source")
                    if not diff_line_count_filter(diff):
                        return
                    for c in detailed_visited_commits:
                        if diff.is_duplicate_of(c):
                            return
                    detailed_visited_commits.append(diff)
                    if is_referenced_commit:
                        referenced_commits[commit_id] = True

                visited_commits = {}
                if type(x["pull_request_merge_commit_sha"]) == str:
                    commit_id = x["pull_request_merge_commit_sha"]
                    operation(x, commit_id)
                    visited_commits[commit_id] = True
                for url in ast.literal_eval(x["events_merged_commit_urls"]):
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    operation(x, commit_id)
                    visited_commits[commit_id] = True
                for item in ast.literal_eval(x["events_other_commit_events_and_urls"]):
                    commit_id = utils.get_commit_id_from_url(item[item.find(':') + 1:])
                    if commit_id in visited_commits:
                        continue
                    operation(x, commit_id)
                    visited_commits[commit_id] = True
                for url in ast.literal_eval(x["events_referenced_commit_urls"]):
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    operation(x, commit_id, True)
                    visited_commits[commit_id] = True
                qualified_non_duplicate_referenced_commits_count.append(str(len(referenced_commits)))

            # local results
    # final global results
    file = open(os.path.join(output_dir, "qualified_non_duplicate_referenced_commits_count.csv"), "w+")
    file.write("count\n" + '\n'.join(qualified_non_duplicate_referenced_commits_count))
    file.close()

def main():
    if len(sys.argv) != 4:
        print("Use: python extract_commit_stats.py issues-directory code-directory output-directory")
        exit()
    extract_large_commit_diffs(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__main__":
    main()
