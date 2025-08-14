import os
import re
import json
from datetime import datetime
from typing import List, Dict, Tuple, Any

import pandas as pd
import requests

TS_RE = re.compile(r"technical_data_(\d{4}-\d{2}-\d{2}T\d{6}Z)\.json", re.I)


class GitHubAPI:
    """Wrapper around GitHub API for easier mocking in tests."""
    def __init__(self, owner: str, repo: str, token: str = None, session=None):
        self.owner = owner
        self.repo = repo
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.session = session or requests.Session()

    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}"
        r = self.session.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def download_json(self, url: str) -> Any:
        r = self.session.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()


def find_latest_file(files: List[Dict[str, Any]]) -> Tuple[datetime, str, str]:
    candidates = []
    for f in files:
        if f.get("type") != "file" or not f["name"].endswith(".json"):
            continue
        m = TS_RE.match(f["name"])
        if not m:
            continue
        ts = datetime.strptime(m.group(1), "%Y-%m-%dT%H%M%SZ")
        candidates.append((ts, f["download_url"], f["name"]))
    if not candidates:
        raise RuntimeError("No matching JSON files found.")
    return max(candidates, key=lambda x: x[0])


def extract_record_list(j: Any) -> List[Dict[str, Any]]:
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for key in ("assets", "data", "items", "results"):
            if key in j and isinstance(j[key], list):
                return j[key]
        for v in j.values():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v[:10]):
                return v
    raise ValueError("Could not find a list of records.")


def load_latest_technical_data_df(github_api: GitHubAPI, path: str) -> pd.DataFrame:
    files = github_api.list_dir(path)
    latest_ts, latest_url, latest_name = find_latest_file(files)
    j = github_api.download_json(latest_url)
    records = extract_record_list(j)

    df = pd.DataFrame(records)

    # Ensure nested dict columns are stored as JSON strings
    for col in df.columns:
        if isinstance(df[col].iloc[0], dict):
            df[col] = df[col].apply(json.dumps)

    df['ymd'] = pd.to_datetime(latest_ts).date()
    return df


def create_table_if_not_exists(ch_client, ddl_path: str, table_check_sql: str):
    table_exists = bool(
        ch_client.query(table_check_sql).result_set
    )
    if not table_exists:
        with open(ddl_path, 'r') as file:
            ddl = file.read()
        ch_client.command(ddl)
    return not table_exists  # Returns True if table was created


def insert_technical_data(ch_client, table_name: str, df: pd.DataFrame):
    ch_client.insert_df(table_name, df)


def main():
    from connections.clickhouse_client import ClickHouseClient

    OWNER = "FlexPwr"
    REPO = "DataEngineeringChallenge"
    PATH = "src/vpp/technical_data"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    github_api = GitHubAPI(OWNER, REPO, GITHUB_TOKEN)
    df = load_latest_technical_data_df(github_api, PATH)
    print("Shape:", df.shape)

    ch_client = ClickHouseClient().get_client()
    ddl_path = '/home/adminabhi/gitrepo/FlexPwr_DE_Challenge/src/ingestion/ddl/flexpwr_raw.technical_data.sql'
    table_check_sql = """
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_catalog='flexpwr_raw' 
          AND table_name='technical_data'
    """

    created = create_table_if_not_exists(ch_client, ddl_path, table_check_sql)
    if created:
        print("Table created.")

    print("Inserting data into ClickHouse...")
    insert_technical_data(ch_client, 'flexpwr_raw.technical_data', df)
    print("Data inserted successfully.")


if __name__ == "__main__":
    main()
