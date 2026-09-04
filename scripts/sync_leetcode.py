#!/usr/bin/env python3
"""
Sync LeetCode stats and submission calendar for Programmer_Sid via GraphQL API.
Outputs to data/leetcode.json.
No external pip dependencies required (uses built-in urllib and json).
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

USERNAME = "Programmer_Sid"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")

GRAPHQL_URL = "https://leetcode.com/graphql"

GRAPHQL_QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submissionCalendar
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
    profile {
      ranking
      reputation
    }
  }
}
"""


def fetch_leetcode_data(username: str):
    payload = json.dumps({
        "query": GRAPHQL_QUERY,
        "variables": {"username": username}
    }).encode("utf-8")

    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://leetcode.com/u/{username}/"
        }
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} received from LeetCode GraphQL")
        body = resp.read().decode("utf-8")
        data = json.loads(body)

    matched_user = data.get("data", {}).get("matchedUser")
    if not matched_user:
        raise ValueError(f"Could not find user '{username}' on LeetCode")

    ac_nums = matched_user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
    ac_map = {item.get("difficulty"): item.get("count", 0) for item in ac_nums}

    cal_str = matched_user.get("submissionCalendar", "{}")
    calendar = json.loads(cal_str) if cal_str else {}

    ranking = matched_user.get("profile", {}).get("ranking", 0)

    result = {
        "username": username,
        "totalSolved": ac_map.get("All", 0),
        "easySolved": ac_map.get("Easy", 0),
        "mediumSolved": ac_map.get("Medium", 0),
        "hardSolved": ac_map.get("Hard", 0),
        "ranking": ranking,
        "activeDays": len(calendar),
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submissionCalendar": calendar
    }

    return result


def main():
    print(f"Fetching LeetCode stats for @{USERNAME}...")
    try:
        data = fetch_leetcode_data(USERNAME)
        print(f"Success! Solved: {data['totalSolved']} (Easy: {data['easySolved']}, Medium: {data['mediumSolved']}, Hard: {data['hardSolved']}), Active Days: {data['activeDays']}")
    except Exception as e:
        print(f"Error fetching from LeetCode: {e}", file=sys.stderr)
        # If output file already exists, don't overwrite with failure
        if os.path.exists(OUTPUT_PATH):
            print("Existing data/leetcode.json preserved.", file=sys.stderr)
            sys.exit(0)
        else:
            sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote updated data to {os.path.normpath(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
