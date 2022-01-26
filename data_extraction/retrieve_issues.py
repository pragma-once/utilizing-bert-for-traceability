# To retrieve closed issues from a repository and extract to a csv file.
# Set the variables in github_token before running.

import json
import requests
import sys
import github_token

def convert_to_csv_field(text):
    text = str(text)
    text = text.replace('"', '""')
    return '"' + text + '"'

"""
repo_name: in owner/repo format
"""
def retrieve_issues(repo_name: str):
    # For example, try https://api.github.com/repos/octocat/Hello-World/issues

    labels = []
    data = []

    page = 1
    while True:
        print("Retrieving page " + str(page) + "...")
        result = requests.get(
            "https://api.github.com/repos/" + repo_name + "/issues",
            params={
                "state": "closed",
                "per_page": "100",
                "page": str(page)
            },
            auth=(github_token.username, github_token.token)
        )
        if result.status_code != 200:
            print("ERROR")
            print("Status code: " + str(result.status_code))
            print("Response: " + result.text)
            return
        print("Processing page " + str(page) + "...")
        result_json = json.loads(result.text)
        if len(result_json) == 0:
            break

        for item in result_json:
            print("Retrieving and processing issue " + str(item["number"]) + "...")
            data_item = {}
            data_item["number"] = item["number"]
            data_item["title"] = item["title"]
            data_item["body"] = item["body"]
            data_item["comments_count"] = item["comments"]
            data_item["comments"] = []
            #print("Retrieving comments for " + str(item["number"]) + "...")
            comments = json.loads(
                requests.get(
                    item["comments_url"],
                    auth=(github_token.username, github_token.token)
                ).text
            )
            for comment in comments:
                data_item["comments"].append(comment["body"])
            data_item["labels"] = []
            for label in item["labels"]:
                label_name = label["name"]
                if label_name not in labels:
                    labels.append(label_name)
                data_item["labels"].append(label_name)
            if "pull_request" in item:
                data_item["is_pull_request"] = 1
                #print("Retrieving pull request for " + str(item["number"]) + "...")
                pr = json.loads(
                    requests.get(
                        item["pull_request"]["url"],
                        auth=(github_token.username, github_token.token)
                    ).text
                )
                data_item["pull_request_merge_commit_sha"] = pr["merge_commit_sha"]
            else:
                data_item["is_pull_request"] = 0
                data_item["pull_request_merge_commit_sha"] = ""
            #print("Retrieving events for " + str(item["number"]) + "...")
            events = json.loads(
                requests.get(
                    item["events_url"],
                    auth=(github_token.username, github_token.token)
                ).text
            )
            data_item["events_referenced_commit_urls"] = []
            data_item["events_merged_commit_urls"] = []
            data_item["events_other_commit_events_and_urls"] = []
            for event in events:
                if event["event"] == "referenced":
                    data_item["events_referenced_commit_urls"].append(event["commit_url"])
                elif event["event"] == "merged":
                    data_item["events_merged_commit_urls"].append(event["commit_url"])
                elif "commit_url" in event and event["commit_url"] is not None and len(event["commit_url"]) > 0:
                    data_item["events_other_commit_urls"].append(event["event"] + ':' + event["commit_url"])
            data.append(data_item)

        page += 1

    print("Processing data...")
    # csv header
    text = (
        "number,title,body,comments_count,comments,labels"
        + ",is_pull_request,pull_request_merge_commit_sha"
        + ",events_referenced_commit_urls,events_merged_commit_urls,events_other_commit_events_and_urls"
    )
    for label in labels:
        text += ',' + convert_to_csv_field("label_" + label)
    # csv data
    for data_item in data:
        text += '\n'
        text += convert_to_csv_field(data_item["number"])
        text += ',' + convert_to_csv_field(data_item["title"])
        text += ',' + convert_to_csv_field(data_item["body"])
        text += ',' + convert_to_csv_field(data_item["comments_count"])
        text += ',' + convert_to_csv_field(data_item["comments"])
        text += ',' + convert_to_csv_field(data_item["labels"])
        text += ',' + convert_to_csv_field(data_item["is_pull_request"])
        text += ',' + convert_to_csv_field(data_item["pull_request_merge_commit_sha"])
        text += ',' + convert_to_csv_field(data_item["events_referenced_commit_urls"])
        text += ',' + convert_to_csv_field(data_item["events_merged_commit_urls"])
        text += ',' + convert_to_csv_field(data_item["events_other_commit_events_and_urls"])
        for label in labels:
            text += ",1" if label in data_item["labels"] else ",0"
    print("Writing to file...")
    file = open(repo_name.replace('/', '_') + ".csv", 'w+')
    file.write(text)
    file.close()

def main():
    if len(sys.argv) < 2:
        print("Use: python retrieve_issues.py repo_owner/repo_name")
        exit()
    retrieve_issues(sys.argv[1])

if __name__ == "__main__":
    main()
