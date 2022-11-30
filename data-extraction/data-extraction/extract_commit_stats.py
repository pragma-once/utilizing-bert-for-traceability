"""
To get commit file counts. Useful (combined with summerize_commit_stats) to choose MAX_FILES_IN_A_COMMIT for process_issues.py.
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

def extract_commit_stats(input_issues_dir: str, input_code_dir: str, output_stats_dir: str):
    all_commit_files_count_dict = {}
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
            print("Processing " + repo_name +  " (" + input_file_name + ")...")
            data = pandas.read_csv(input_file_path)

            def count_commit_files(commit_id):
                try:
                    commit = repo.commit(commit_id)
                except:
                    return -1

                return len([f for f in commit.stats.files if f.endswith(".java")])

            all_commit_files_count_dict[repo_name] = {}
            commit_files_count_dict = {}
            for row in data.iterrows():
                x = row[1]
                labels = ast.literal_eval(x["labels"])
                for label in labels:
                    if any(
                                word in label.lower()
                                    for word in LABEL_WORDS_TO_AVOID
                            ):
                        continue

                def add_count(issue_number, commit_id):
                    count = count_commit_files(commit_id)
                    if count == -1:
                        return
                    if issue_number not in commit_files_count_dict:
                        commit_files_count_dict[issue_number] = {}
                    commit_files_count_dict[issue_number][commit_id] = count
                    if issue_number not in all_commit_files_count_dict[repo_name]:
                        all_commit_files_count_dict[repo_name][issue_number] = {}
                    all_commit_files_count_dict[repo_name][issue_number][commit_id] = count

                visited_commits = {}
                if type(x["pull_request_merge_commit_sha"]) == str:
                    commit_id = x["pull_request_merge_commit_sha"]
                    add_count(x["number"], commit_id)
                    visited_commits[commit_id] = True
                for url in ast.literal_eval(x["events_referenced_commit_urls"]):
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    add_count(x["number"], commit_id)
                    visited_commits[commit_id] = True
                for url in ast.literal_eval(x["events_merged_commit_urls"]):
                    commit_id = utils.get_commit_id_from_url(url)
                    if commit_id in visited_commits:
                        continue
                    add_count(x["number"], commit_id)
                    visited_commits[commit_id] = True
                for item in ast.literal_eval(x["events_other_commit_events_and_urls"]):
                    commit_id = utils.get_commit_id_from_url(item[item.find(':') + 1:])
                    if commit_id in visited_commits:
                        continue
                    add_count(x["number"], commit_id)
                    visited_commits[commit_id] = True

            output_csv = "issue_number,commit_id,files_count"
            for issue_number in commit_files_count_dict:
                for commit_id in commit_files_count_dict[issue_number]:
                    output_csv += "\n"
                    output_csv += str(issue_number)
                    output_csv += ","
                    output_csv += commit_id
                    output_csv += ","
                    output_csv += str(commit_files_count_dict[issue_number][commit_id])
            file = open(os.path.join(output_stats_dir, repo_name.replace('/', '_') + ".csv"), "w+")
            file.write(output_csv)
    output_csv = "repo_name/issue_number,repo_name,issue_number,commit_id,files_count"
    for repo_name in all_commit_files_count_dict:
        for issue_number in all_commit_files_count_dict[repo_name]:
            for commit_id in all_commit_files_count_dict[repo_name][issue_number]:
                output_csv += "\n"
                output_csv += repo_name + '/' + str(issue_number)
                output_csv += ","
                output_csv += repo_name
                output_csv += ","
                output_csv += str(issue_number)
                output_csv += ","
                output_csv += commit_id
                output_csv += ","
                output_csv += str(all_commit_files_count_dict[repo_name][issue_number][commit_id])
    file = open(os.path.join(output_stats_dir, "all.csv"), "w+")
    file.write(output_csv)

def main():
    if len(sys.argv) != 4:
        print("Use: python extract_commit_stats.py issues-directory code-directory output-commit-stats-directory")
        exit()
    extract_commit_stats(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == "__main__":
    main()
