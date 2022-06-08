"""
Step 4.
To extract issue-code links.
"""

import ast
from hashlib import new
import git
import json
import os
import pandas
import sys
import utils

# enum
DIFF_LINES_AS_CODE = 0
METHODS_AS_CODE = 1

CODE_CONTENT = METHODS_AS_CODE

MIN_CODE_LINES_IN_A_COMMIT = 6

COUNT_REMOVED_FILES_LINES_FOR_MIN_LINES = True
COUNT_MODIFIED_FILES_REMOVED_LINES_FOR_MIN_LINES = True

# Commits with more files are ignored.
MAX_FILES_IN_A_COMMIT = 10

# Diffs with more lines of difference are ignored
MAX_DIFF_LINES = 1000

# A constraint for when METHODS_AS_CODE is used
# This is a constraint in the Java code.
#MINIMUM_METHOD_COMMIT_LINES = 1

def extract_data(input_issues_dir: str, input_code_dir: str, output_issue_code_dir: str):
    for input_file_name in os.listdir(input_issues_dir):
        input_file_path = os.path.join(input_issues_dir, input_file_name)
        if os.path.isfile(input_file_path) and input_file_path.endswith(".csv"):
            if os.path.exists(os.path.join(output_issue_code_dir, input_file_name)):
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

            def count_commit_lines(diff: utils.CommitDiff):
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

            def diff_line_count_filter(diff: utils.CommitDiff):
                return count_commit_lines(diff) >= MIN_CODE_LINES_IN_A_COMMIT

            def get_diffs_of_issue(x) -> list[utils.CommitDiff]:
                visited_commits = {}
                diffs: list[utils.CommitDiff] = []

                def add_diff(commit: git.Commit):
                    if len([f for f in commit.stats.files if f.endswith(".java")]) > MAX_FILES_IN_A_COMMIT:
                        return
                    new_diff = utils.CommitDiff(commit, mime_type="text/x-java-source")
                    for diff in diffs:
                        if new_diff.is_duplicate_of(diff):
                            #print("[TEST] Found a duplicate! " + diff.commit.hexsha + " and " + new_diff.commit.hexsha)
                            return
                    if (diff_line_count_filter(new_diff)):
                        diffs.append(new_diff)

                if type(x["pull_request_merge_commit_sha"]) == str: # First priority
                    commit_id = x["pull_request_merge_commit_sha"]
                    try:
                        commit = repo.commit(commit_id)
                        add_diff(commit)
                    except:
                        pass
                    visited_commits[commit_id] = True
                for item in ast.literal_eval(x["events_other_commit_events_and_urls"]): # Second priority
                    commit_id = utils.get_commit_id_from_url(item[item.find(':') + 1:])
                    if commit_id in visited_commits:
                        continue
                    try:
                        commit = repo.commit(commit_id)
                        add_diff(commit)
                    except:
                        pass
                    visited_commits[commit_id] = True
                for url in ast.literal_eval(x["events_merged_commit_urls"]): # Third priority
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    try:
                        commit = repo.commit(commit_id)
                        add_diff(commit)
                    except:
                        pass
                    visited_commits[commit_id] = True
                urls = ast.literal_eval(x["events_referenced_commit_urls"]) # Last priority
                for url in urls: # Last priority
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    try:
                        commit = repo.commit(commit_id)
                        add_diff(commit)
                    except:
                        pass
                    visited_commits[commit_id] = True
                return diffs

            output = []
            if CODE_CONTENT == DIFF_LINES_AS_CODE:
                for row in data.iterrows():
                    x = row[1]
                    diffs = get_diffs_of_issue(x)
                    for diff in diffs:
                        code = ""
                        for item in diff.added_files:
                            if len(item.text.splitlines()) > MAX_DIFF_LINES:
                                continue
                            code += item.text
                        for item in diff.removed_files:
                            if len(item.text.splitlines()) > MAX_DIFF_LINES:
                                continue
                            code += item.text
                        for item in diff.modified_files:
                            if len(item.added_lines) + len(item.removed_lines) > MAX_DIFF_LINES:
                                continue
                            if item.new_file_info.mime_type == "text/x-java-source" and item.old_file_info.mime_type == "text/x-java-source":
                                lines = item.added_lines + item.removed_lines
                                lines.sort(key=lambda x: x.line_index)
                                code += '\n'.join([line.line_text for line in lines])
                            elif item.new_file_info.mime_type == "text/x-java-source":
                                code += '\n'.join([line.line_text for line in item.added_lines])
                            elif item.old_file_info.mime_type == "text/x-java-source":
                                code += '\n'.join([line.line_text for line in item.removed_lines])
                        if len(code) != 0:
                            output.append(
                                {
                                    "issue_number": x["number"],
                                    "issue_title": x["title"],
                                    "issue_body": x["body"],
                                    "issue_comments": x["comments"],
                                    "issue_text": str(x["title"]) + '\n' + str(x["body"]),
                                    "commit_id": diff.commit.hexsha,
                                    "commit_message": diff.commit.message.strip(),
                                    "code": code
                                }
                            )
            elif CODE_CONTENT == METHODS_AS_CODE: # Needs to be processed in Java.
                for row in data.iterrows():
                    x = row[1]
                    diffs = get_diffs_of_issue(x)
                    for diff in diffs:
                        code = {}
                        code["added_files"] = []
                        code["removed_files"] = []
                        code["modified_files"] = []
                        for item in diff.added_files:
                            if len(item.text.splitlines()) > MAX_DIFF_LINES:
                                continue
                            added_file = {}
                            added_file["path"] = item.path
                            added_file["text"] = item.text
                            code["added_files"].append(added_file)
                        for item in diff.removed_files:
                            if len(item.text.splitlines()) > MAX_DIFF_LINES:
                                continue
                            removed_file = {}
                            removed_file["path"] = item.path
                            removed_file["text"] = item.text
                            code["removed_files"].append(removed_file)
                        for item in diff.modified_files:
                            if len(item.added_lines) + len(item.removed_lines) > MAX_DIFF_LINES:
                                continue
                            modified_file = {}
                            modified_file["old_mime_type"] = item.old_file_info.mime_type
                            modified_file["new_mime_type"] = item.new_file_info.mime_type
                            modified_file["old_path"] = item.old_file_info.path
                            modified_file["new_path"] = item.new_file_info.path
                            modified_file["old_text"] = item.old_file_info.text
                            modified_file["new_text"] = item.new_file_info.text
                            modified_file["removed_lines"] = [{ "index": line.line_index, "text": line.line_text } for line in item.removed_lines]
                            modified_file["added_lines"] = [{ "index": line.line_index, "text": line.line_text } for line in item.added_lines]
                            #modified_file["nonempty_removed_lines"] = [{ "index": line.line_index, "text": line.line_text } for line in item.removed_lines if len(line.line_text.strip()) != 0]
                            #modified_file["nonempty_added_lines"] = [{ "index": line.line_index, "text": line.line_text } for line in item.added_lines if len(line.line_text.strip()) != 0]
                            code["modified_files"].append(modified_file)
                        if len(code) != 0:
                            output.append(
                                {
                                    "issue_number": x["number"],
                                    "issue_title": x["title"],
                                    "issue_body": x["body"],
                                    "issue_comments": x["comments"],
                                    "issue_text": str(x["title"]) + '\n' + str(x["body"]),
                                    "commit_id": diff.commit.hexsha,
                                    "commit_message": diff.commit.message.strip(),
                                    "code": code
                                }
                            )

            output_lines = []
            for item in output:
                output_lines.append(json.dumps(item))
            output_file = open(os.path.join(output_issue_code_dir, repo_name.replace('/', '_') + "_0.jsonl"), "w+")
            output_file.write('\n'.join(output_lines))
            output_file.close()

def notice_code_content():
    print("----------------------------------------------------------------")
    if CODE_CONTENT == DIFF_LINES_AS_CODE:
        print("CODE_CONTENT is set to DIFF_LINES_AS_CODE.")
        print("The output files are final.")
    if CODE_CONTENT == METHODS_AS_CODE:
        print("CODE_CONTENT is set to METHODS_AS_CODE.")
        print("The next step is to process the output files with the Java program 'extract-data-java-methods'.")
    print("----------------------------------------------------------------")

def main():
    if len(sys.argv) != 4:
        print("Use: python extract_data.py issues-directory code-directory output-issue-code-data-directory")
        exit()
    notice_code_content()
    extract_data(sys.argv[1], sys.argv[2], sys.argv[3])
    notice_code_content()

if __name__ == "__main__":
    main()
