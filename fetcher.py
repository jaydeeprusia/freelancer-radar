import requests
import pandas as pd

BASE_URL = "https://www.freelancer.com/api/projects/0.1/projects/active"


def fetch_projects(auth_token, limit=20, max_price=100, pages=3):
    all_projects = []

    headers = {
        "freelancer-auth-v2": auth_token,
        "freelancer-app-name": "main",
        "freelancer-app-platform": "web",
        "Accept": "application/json",
    }

    for page in range(pages):
        params = {
            "limit": limit,
            "offset": page * limit,
            "full_description": "true",
            "job_details": "true",
            "owner_info": "true",
            "project_types[]": "fixed",
            "sort_field": "bid_count",
            "reverse_sort": "true",
            "max_price": max_price,
        }

        response = requests.get(BASE_URL, headers=headers, params=params)

        if response.status_code != 200:
            print("Error:", response.text)
            break

        data = response.json()

        # Adjust depending on actual response structure
        projects = data.get("result", {}).get("projects", [])

        if not projects:
            break

        all_projects.extend(projects)

    return pd.DataFrame(all_projects)
