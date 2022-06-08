"""
Step 3.
To pre-process issues data.
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

COUNT_REMOVED_FILES_LINES_FOR_MIN_LINES = True
COUNT_MODIFIED_FILES_REMOVED_LINES_FOR_MIN_LINES = True

# Commits with more files are ignored.
MAX_FILES_IN_A_COMMIT = 10

# Diffs with more lines of difference are ignored
MAX_DIFF_LINES = 1000

def process_issues(input_issues_dir: str, input_code_dir: str, output_issues_dir: str):
    label_dict = {}
    issues_count_before_processing = 0
    issues_count_after_processing = 0
    issues_discarded_by_label_words_dict = {}
    for input_file_name in os.listdir(input_issues_dir):
        input_file_path = os.path.join(input_issues_dir, input_file_name)
        if os.path.isfile(input_file_path) and input_file_path.endswith(".csv"):
            if os.path.exists(os.path.join(output_issues_dir, input_file_name)):
                continue
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
            print("Processing " + repo_name +  " (" + input_file_name + ")...")
            data = pandas.read_csv(input_file_path)

            def count_commit_lines(commit_id):
                try:
                    commit = repo.commit(commit_id)
                except:
                    return 0

                if len([f for f in commit.stats.files if f.endswith(".java")]) > MAX_FILES_IN_A_COMMIT:
                    return 0

                count = 0

                diff = utils.CommitDiff(commit, mime_type="text/x-java-source")
                count = 0
                for item in diff.added_files:
                    lines = item.text.splitlines()
                    if len(lines) > MAX_DIFF_LINES:
                        continue
                    # Doesn't count empty lines
                    count += len([1 for line in lines if len(line.strip()) != 0])
                if COUNT_REMOVED_FILES_LINES_FOR_MIN_LINES:
                    for item in diff.removed_files:
                        lines = item.text.splitlines()
                        if len(lines) > MAX_DIFF_LINES:
                            continue
                        count += len([1 for line in lines if len(line.strip()) != 0])
                for item in diff.modified_files:
                    if len(item.added_lines) + len(item.removed_lines) > MAX_DIFF_LINES:
                        continue
                    if item.new_file_info.mime_type == "text/x-java-source":
                        # Doesn't count empty lines
                        count += len([1 for line in item.added_lines if len(line.line_text.strip()) != 0])
                    if COUNT_MODIFIED_FILES_REMOVED_LINES_FOR_MIN_LINES and item.old_file_info.mime_type == "text/x-java-source":
                        count += len([1 for line in item.removed_lines if len(line.line_text.strip()) != 0])
                return count

            local_issues_discarded_by_label_words_dict = {}
            def filter_func(x):
                labels = ast.literal_eval(x["labels"])
                for label in labels:
                    if any(
                                word in label.lower()
                                    for word in LABEL_WORDS_TO_AVOID
                            ):
                        local_issues_discarded_by_label_words_dict[x["number"]] = True
                        issues_discarded_by_label_words_dict[repo_name + '/' + str(x["number"])] = True
                        return False
                    label_dict[label] = True
                # Check commit lines count
                lines_count_max = 0
                visited_commits = {}
                if type(x["pull_request_merge_commit_sha"]) == str:
                    commit_id = x["pull_request_merge_commit_sha"]
                    lines_count_max = max(lines_count_max, count_commit_lines(commit_id))
                    visited_commits[commit_id] = True
                for url in ast.literal_eval(x["events_merged_commit_urls"]):
                    if lines_count_max >= MIN_CODE_LINES_IN_A_COMMIT:
                        break
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    lines_count_max = max(lines_count_max, count_commit_lines(commit_id))
                    visited_commits[commit_id] = True
                for item in ast.literal_eval(x["events_other_commit_events_and_urls"]):
                    if lines_count_max >= MIN_CODE_LINES_IN_A_COMMIT:
                        break
                    commit_id = utils.get_commit_id_from_url(item[item.find(':') + 1:])
                    if commit_id in visited_commits:
                        continue
                    lines_count_max = max(lines_count_max, count_commit_lines(commit_id))
                    visited_commits[commit_id] = True
                urls = ast.literal_eval(x["events_referenced_commit_urls"])
                for url in urls:
                    if lines_count_max >= MIN_CODE_LINES_IN_A_COMMIT:
                        break
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    lines_count_max = max(lines_count_max, count_commit_lines(commit_id))
                    visited_commits[commit_id] = True
                if lines_count_max < MIN_CODE_LINES_IN_A_COMMIT:
                    return False
                return True
            processed_data = data[data.apply(filter_func, axis=1)]
            processed_data.reset_index(drop=True).to_csv(os.path.join(output_issues_dir, repo_name.replace('/', '_') + ".csv"))
            print("Before processing: " + str(len(data)) + " issues")
            print("After processing: " + str(len(processed_data)) + " issues")
            print("Number of issues discarded by label words: " + str(len(local_issues_discarded_by_label_words_dict)))
            # Test:
            #if "label_dependencies" in data.columns:
            #    print(data[data["label_dependencies"] == 1]["label_dependencies"].count())
            #    print(processed_data[processed_data["label_dependencies"] == 1]["label_dependencies"].count())
            print()
            issues_count_before_processing += len(data)
            issues_count_after_processing += len(processed_data)
    #print("All labels:")
    #print([key for key in label_dict])
    print("Original issues count: " + str(issues_count_before_processing))
    print(
        "Processed issues count: " + str(issues_count_after_processing)
        + " (" + str(100 * issues_count_after_processing / issues_count_before_processing) + "%)"
    )
    print(
        "Number of issues discarded by label words: " + str(len(issues_discarded_by_label_words_dict))
        + " (" + str(100 * len(issues_discarded_by_label_words_dict) / issues_count_before_processing) + "%)"
    )

def main():
    if len(sys.argv) != 4:
        print("Use: python process_issues.py issues-directory code-directory output-processed-issues-directory")
        exit()
    process_issues(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__main__":
    main()
