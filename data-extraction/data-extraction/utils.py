import ast
import collections
import hashlib
from types import NoneType
import git
import pandas

import cutils

if cutils.diff_library == None:
    print("Could not load the library for diff. The Python implementation will be used instead.")
else:
    print("Diff library loaded. The C++ implementation will be used for diff.")

def discover_repo_address_from_issue_data(file_full_path: str, file_name: str, force_check_commit_urls: bool = False):
    separator = file_name.find('_')
    if separator == -1:
        return None
    separator2 = file_name.find('_', separator + 1)
    if separator2 == -1 and not force_check_commit_urls:
        end = -4 if file_name.endswith(".csv") else len(file_name)
        return file_name[:separator] + "/" + file_name[separator + 1:end]
    else:
        data = pandas.read_csv(file_full_path)

        def check_url(url):
            url_start = "https://api.github.com/repos/"
            starting_name = file_name[:separator]
            if url.startswith(url_start + starting_name):
                s1 = url.find('/', len(url_start))
                if s1 == -1:
                    return None
                s2 = url.find('/', s1 + 1)
                if s2 == -1:
                    return None # Shouldn't happen
                repo_name = url[len(url_start):s2]
                if repo_name.replace('/', '_') + ".csv" == file_name:
                    return repo_name
                return None
        for url_list in data["events_referenced_commit_urls"]:
            for url in ast.literal_eval(url_list):
                result = check_url(url)
                if result is not None:
                    return result
        for url_list in data["events_merged_commit_urls"]:
            for url in ast.literal_eval(url_list):
                result = check_url(url)
                if result is not None:
                    return result
        for url_list in data["events_other_commit_events_and_urls"]:
            for item in ast.literal_eval(url_list):
                result = check_url(item[item.find(':') + 1:])
                if result is not None:
                    return result
        return None

def get_commit_id_from_url(url: str):
    url_target = "commits/"
    i = url.rfind(url_target)
    if i == -1:
        return None
    i += len(url_target)
    j = -1 if url.endswith('/') else len(url)
    return url[i:j]

class FileInfo:
    def __init__(self, path: str, text: str | NoneType, mime_type: str, blob: git.Blob):
        self.path = path
        self.text = text
        self.mime_type = mime_type
        self.blob = blob

def _get_file_info(commit: git.Commit, path: str, blob: git.Blob):
    return FileInfo(
        path,
        commit.repo.git.show('{}:{}'.format(commit.hexsha, path)) if blob.mime_type.startswith("text") else None,
        blob.mime_type,
        blob
    )

class LineInfo:
    def __init__(self, line_index: int, line_text: str):
        self.line_index = line_index
        self.line_text = line_text

"""
Myers difference algorithm
"""
class Diff:
    def __init__(self, old_list: list[str], new_list: list[str]):
        self.removed_items = []
        self.added_items = []

        try:
            old_list_hash = [hashlib.sha256(item.encode("utf-8")).digest() for item in old_list]
            new_list_hash = [hashlib.sha256(item.encode("utf-8")).digest() for item in new_list]
        except:
            print("[WARNING] There was a problem encoding a file's text for diff. Skipping as it would also cause more problems later.")
            return

        if len(old_list) == 0 or len(new_list) == 0:
            return

        if cutils.diff_library != None:
            result = cutils.diff(old_list_hash, new_list_hash) # Faster C++ implementation
            self.removed_items = [(i, old_list[i]) for i in result["removed_items"]]
            self.added_items = [(i, new_list[i]) for i in result["added_items"]]
            return

        # Based on:
        # https://gist.github.com/adamnew123456/37923cf53f51d6b9af32a539cdfa7cc4

        Frontier = collections.namedtuple('Frontier', ['x', 'history'])
        frontier = {1: Frontier(0, [])}

        def one(idx):
            """
            The algorithm Myers presents is 1-indexed; since Python isn't, we
            need a conversion.
            """
            return idx - 1

        a_max = len(old_list)
        b_max = len(new_list)
        for d in range(0, a_max + b_max + 1):
            for k in range(-d, d + 1, 2):
                go_down = (k == -d or (k != d and frontier[k - 1].x < frontier[k + 1].x))

                if go_down:
                    old_x, history = frontier[k + 1]
                    x = old_x
                else:
                    old_x, history = frontier[k - 1]
                    x = old_x + 1

                history = history[:]
                y = x - k

                if 1 <= y <= b_max and go_down:
                    history.append((one(x), one(y), 2)) # insert
                elif 1 <= x <= a_max:
                    history.append((one(x), one(y), 1)) # remove

                while x < a_max and y < b_max and old_list_hash[one(x + 1)] == new_list_hash[one(y + 1)]:
                    x += 1
                    y += 1
                    history.append((one(x), one(y), 0)) # keep

                if x >= a_max and y >= b_max:
                    # done
                    for item in history:
                        if item[2] == 1:
                            removed_index = item[0]
                            self.removed_items.append((removed_index, old_list[removed_index]))
                        if item[2] == 2:
                            added_index = item[1]
                            self.added_items.append((added_index, new_list[added_index]))
                    return
                else:
                    frontier[k] = Frontier(x, history)

class FileModificationInfo:
    """
    Lines are 0-based indices.
    Removed lines are from the old file, and added lines are from the new file.
    """
    def __init__(self, old_file_info: FileInfo, new_file_info: FileInfo, renamed: bool):
        self.old_file_info = old_file_info
        self.new_file_info = new_file_info
        self.renamed = renamed
        self.removed_lines: list[LineInfo] = []
        self.added_lines: list[LineInfo] = []

        if old_file_info.text is not None and new_file_info.text is not None:
            # find lines diff
            old_lines: list[str] = old_file_info.text.splitlines()
            new_lines: list[str] = new_file_info.text.splitlines()

            diff = Diff(old_lines, new_lines)
            self.added_lines = [LineInfo(item[0], item[1]) for item in diff.added_items]
            self.removed_lines = [LineInfo(item[0], item[1]) for item in diff.removed_items]

"""
To get the diff from a commit
"""
class CommitDiff:
    def __init__(self, commit: git.Commit, mime_type: str | NoneType = None):
        self.commit = commit
        self.added_files: list[FileInfo] = []
        self.removed_files: list[FileInfo] = []
        self.modified_files: list[FileModificationInfo] = []
        self.added_files_dict: dict[str, FileInfo] = {}
        self.removed_files_dict: dict[str, FileInfo] = {}
        self.modified_files_dict: dict[str, FileModificationInfo] = {}

        if commit is None:
            return

        for filename in commit.stats.files:
            if ':' in filename:
                print(
                    "[WARNING] Found ':' in a filename in diff of commit "
                    + commit.hexsha
                    + ". Skipping to avoid gitpython failure."
                ) # Issue: https://github.com/gitpython-developers/GitPython/issues/1210
                return

        if len(commit.parents) == 0:
            return
        parent = commit.parents[0]
        diffs = parent.diff(commit)
        for diff in diffs:
            if diff.new_file:
                if mime_type is None or diff.b_blob.mime_type == mime_type:
                    file_info = _get_file_info(commit, diff.b_path, diff.b_blob)
                    self.added_files.append(file_info)
                    self.added_files_dict[file_info.path] = file_info
            elif diff.deleted_file:
                if mime_type is None or diff.a_blob.mime_type == mime_type:
                    file_info = _get_file_info(parent, diff.a_path, diff.a_blob)
                    self.removed_files.append(file_info)
                    self.removed_files_dict[file_info.path] = file_info
            else:
                if mime_type is None or diff.a_blob.mime_type == mime_type or diff.b_blob.mime_type == mime_type:
                    modification_info = FileModificationInfo(
                        _get_file_info(parent, diff.a_path, diff.a_blob),
                        _get_file_info(commit, diff.b_path, diff.b_blob),
                        diff.renamed_file
                    )
                    self.modified_files.append(modification_info)
                    self.modified_files_dict[modification_info.new_file_info.path] = modification_info

    def is_duplicate_of(self, other):
        if len(self.added_files_dict) != len(other.added_files_dict):
            return False
        if len(self.removed_files_dict) != len(other.removed_files_dict):
            return False
        if len(self.modified_files_dict) != len(other.modified_files_dict):
            return False
        for path in self.added_files_dict:
            if path not in other.added_files_dict:
                return False
        for path in self.removed_files_dict:
            if path not in other.removed_files_dict:
                return False
        for path in self.modified_files_dict:
            if path not in other.modified_files_dict:
                return False
        for path in self.added_files_dict:
            if self.added_files_dict[path].text != other.added_files_dict[path].text:
                return False
        for path in self.removed_files_dict:
            if self.removed_files_dict[path].text != other.removed_files_dict[path].text:
                return False
        for path in self.modified_files_dict:
            a = self.modified_files_dict[path].added_lines
            b = other.modified_files_dict[path].added_lines
            if len(a) != len(b):
                return False
            for i in range(len(a)):
                if a[i].line_text != b[i].line_text:
                    return False
            a = self.modified_files_dict[path].removed_lines
            b = other.modified_files_dict[path].removed_lines
            if len(a) != len(b):
                return False
            for i in range(len(a)):
                if a[i].line_text != b[i].line_text:
                    return False
        return True

def get_diff_from_url(repo: git.Repo, commit_url: str):
    try:
        commit_id = get_commit_id_from_url(commit_url)
        return CommitDiff(repo.commit(commit_id))
    except:
        return CommitDiff()

def test_get_diff():
    repo_path = input("Enter the repo path: ")
    repo = git.Repo(repo_path)
    for commit in repo.iter_commits():
        diff = CommitDiff(commit)
        pass

def main():
    test_get_diff();

if __name__ == "__main__":
    main()
