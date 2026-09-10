#!/usr/bin/env python3
"""
Sync LeetCode stats and submission calendar for Programmer_Sid.
Primary source: Official LeetCode GraphQL API.
Fallback source: High-availability REST proxy.
Outputs to:
  - data/leetcode.json
  - data/leetcode-data.js (for zero-CORS / offline viewing)
No external pip dependencies required (uses built-in urllib and json).
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

USERNAME = "Programmer_Sid"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
OUTPUT_JSON = os.path.join(DATA_DIR, "leetcode.json")
OUTPUT_JS = os.path.join(DATA_DIR, "leetcode-data.js")

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

FALLBACK_URL = f"https://leetcode-api-faisalshohag.vercel.app/{USERNAME}"


def fetch_from_graphql(username: str):
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

    with urllib.request.urlopen(req, timeout=12) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} received from LeetCode GraphQL")
        body = resp.read().decode("utf-8")
        data = json.loads(body)

    matched_user = data.get("data", {}).get("matchedUser")
    if not matched_user:
        raise ValueError(f"User '{username}' not found in LeetCode GraphQL response")

    ac_nums = matched_user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
    ac_map = {item.get("difficulty"): item.get("count", 0) for item in ac_nums}

    cal_str = matched_user.get("submissionCalendar", "{}")
    calendar = json.loads(cal_str) if isinstance(cal_str, str) else (cal_str or {})

    ranking = matched_user.get("profile", {}).get("ranking", 0)

    return {
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


def fetch_from_fallback(username: str):
    url = f"https://leetcode-api-faisalshohag.vercel.app/{username}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} received from fallback API")
        data = json.loads(resp.read().decode("utf-8"))

    calendar = data.get("submissionCalendar", {})
    if isinstance(calendar, str):
        calendar = json.loads(calendar)

    return {
        "username": username,
        "totalSolved": data.get("totalSolved", 0),
        "easySolved": data.get("easySolved", 0),
        "mediumSolved": data.get("mediumSolved", 0),
        "hardSolved": data.get("hardSolved", 0),
        "ranking": data.get("ranking", 0),
        "activeDays": len(calendar),
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submissionCalendar": calendar
    }


def fetch_leetcode_data(username: str):
    # Try official GraphQL first
    try:
        print("Attempting sync via official LeetCode GraphQL...")
        return fetch_from_graphql(username)
    except Exception as e:
        print(f"GraphQL attempt failed ({e}). Trying fallback REST API...", file=sys.stderr)

    # Try fallback API
    try:
        print("Attempting sync via fallback API...")
        return fetch_from_fallback(username)
    except Exception as e:
        print(f"Fallback attempt failed ({e}).", file=sys.stderr)
        raise RuntimeError(f"All LeetCode sync sources failed for {username}")


def main():
    print(f"Fetching LeetCode stats for @{USERNAME}...")
    try:
        data = fetch_leetcode_data(USERNAME)
        print(f"Success! Solved: {data['totalSolved']} (Easy: {data['easySolved']}, Medium: {data['mediumSolved']}, Hard: {data['hardSolved']}), Active Days: {data['activeDays']}")
    except Exception as e:
        print(f"Error fetching from LeetCode: {e}", file=sys.stderr)
        if os.path.exists(OUTPUT_JSON):
            print("Existing data/leetcode.json preserved.", file=sys.stderr)
            sys.exit(0)
        else:
            sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Write JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote updated JSON to {os.path.normpath(OUTPUT_JSON)}")

    # 2. Write JS file for offline / file:// protocol compatibility
    js_content = f"// Auto-generated by scripts/sync_leetcode.py\nwindow.LEETCODE_STATIC_DATA = {json.dumps(data, indent=2)};\n"
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"Wrote updated JS to {os.path.normpath(OUTPUT_JS)}")


if __name__ == "__main__":
    main()
