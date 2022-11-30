"""
Step 2.
To retrieve the code (repositories) related to the issues.
"""

import git
import os
import sys
import utils

def retrieve_code(input_dir: str, output_dir: str):
    for input_file_name in os.listdir(input_dir):
        input_file_path = os.path.join(input_dir, input_file_name)
        if os.path.isfile(input_file_path) and input_file_path.endswith(".csv"):
            repo_name = utils.discover_repo_address_from_issue_data(input_file_path, input_file_name)
            if repo_name is None:
                print("Could not find out the repo address of '" + input_file_name + "', skipping...")
                continue
            print("Retrieving " + repo_name +  " (" + input_file_name + ")...")
            git.Repo.clone_from("https://github.com/" + repo_name + ".git", os.path.join(output_dir, repo_name.replace('/', '_')))

def main():
    if len(sys.argv) != 3:
        print("Use: python retrieve_code.py issues-directory output-repository-download-directory")
        exit()
    retrieve_code(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
