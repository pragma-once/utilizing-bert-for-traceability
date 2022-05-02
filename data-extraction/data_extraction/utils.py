import ast
import pandas

def discover_repo_address_from_issue_data(file_full_path: str, file_name: str, force_check_commit_urls: bool):
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
                repo = url[len(url_start):s2]
                if repo.replace('/', '_') + ".csv" == file_name:
                    return repo
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
