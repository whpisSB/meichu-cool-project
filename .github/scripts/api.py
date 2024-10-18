#!/usr/bin/env python3

import subprocess
import sys
import json
import requests

commit_users = {}
user_comments = {}
commit_count = {}


def get_commits(token, repo, pr_num):
    global commit_users, user_comments, commit_count

    cmd = f"""
curl -L \
-H "Accept: application/vnd.github+json" \
-H "Authorization: Bearer {token}" \
-H "X-GitHub-Api-Version: 2022-11-28" \
https://api.github.com/repos/{repo}/pulls/{pr_num}/commits
"""
    res = subprocess.run(cmd, capture_output=True, shell=True)
    json_res = json.loads(res.stdout.decode())

    for commit in json_res:
        github_id = commit["author"]["login"]
        sha = commit["sha"]
        commit_users[sha] = github_id
        user_comments[github_id] = []
        commit_count[github_id] = commit_count.get(github_id, 0) + 1

    return commit_users


def get_review_comments(token, repo, pr_num):
    global user_comments
    cmd = f"""
curl -L \
-H "Accept: application/vnd.github+json" \
-H "Authorization: Bearer {token}" \
-H "X-GitHub-Api-Version: 2022-11-28" \
https://api.github.com/repos/{repo}/pulls/{pr_num}/comments
"""
    res = subprocess.run(cmd, capture_output=True, shell=True)
    json_res = json.loads(res.stdout.decode())

    for comment in json_res:
        if comment["user"]["login"] in commit_users.values():
            continue

        original_commit_id = comment["original_commit_id"]

        if original_commit_id in commit_users:
            user = commit_users[original_commit_id]
            user_comments[user].append(
                {"reviewer_id": comment["user"]["login"], "comment": comment["body"]}
            )


def post_request(repo, endpoint):
    contributors = []
    
    for github_id in commit_count.keys():
        contributor = {
            "github_id": github_id,
            "commit_count": commit_count[github_id],
            "review_comments": user_comments[github_id],
        }

        contributors.append(contributor)

    body = {"repository": repo, "contributors": contributors}
    print(json.dumps(body, indent=4))
    requests.post(f"{endpoint}/api/v1/pr", json=body)


if __name__ == "__main__":
    token, repo, pr_num, endpoint = sys.argv[1:5]

    get_commits(token, repo, pr_num)
    get_review_comments(token, repo, pr_num)
    post_request(repo, endpoint)