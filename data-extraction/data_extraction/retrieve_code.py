"""
Step 2.
To retrieve the code (repositories) related to the issues.
"""

import git
import os
import sys
import utils

def retrieve_code(input_dir: str, output_dir: str):
    for input_filename_file in os.listdir(input_dir):
        input_filename = os.path.join(input_dir, input_filename_file)
        if os.path.isfile(input_filename) and input_filename.endswith(".csv"):
            repo = utils.discover_repo_address_from_issue_data(input_filename, input_filename_file, False)
            if repo is None:
                print("Could not find out the repo address of '" + input_filename_file + "', skipping...")
                continue
            print("Retrieving " + repo +  " (" + input_filename_file + ")...")
            git.Repo.clone_from("https://github.com/" + repo + ".git", os.path.join(output_dir, repo.replace('/', '_')))

def main():
    if len(sys.argv) < 3:
        print("Use: python retrieve_code.py issues-directory output-repository-download-directory")
        exit()
    retrieve_code(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
