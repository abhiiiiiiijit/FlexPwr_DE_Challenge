import os
import json
from typing import List, Dict, Any
import pandas as pd
import requests
from pytz import timezone

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


def load_all_files_from_folder(github_api: GitHubAPI, path: str) -> pd.DataFrame:
    files = github_api.list_dir(path)
    json_files = [f for f in files if f.get("type") == "file" and f["name"].endswith(".json")]

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {path}")

    dfs = []

    for file_info in json_files:
        print(f"Processing {file_info['name']}...")
        j = github_api.download_json(file_info["download_url"])

        col_ids = j.get("column_ids", [])
        values = j.get("values", [])

        if not col_ids or not values:
            print(f"Skipping {file_info['name']}: Missing column_ids or values")
            continue

        # Build DataFrame
        data_dict = {col_ids[idx]: values[idx] for idx in range(len(col_ids))}
        df = pd.DataFrame(data_dict)

        if "timestamp" not in df.columns:
            print(f"Skipping {file_info['name']}: No 'timestamp' column")
            continue

        # Assuming df["timestamp"] contains timestamps in milliseconds (UTC)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Extract year-month-day for CEST (Europe/Berlin) without modifying timestamp
        df["ymd"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Europe/Berlin").dt.date

        # Add metadata from "key"
        if "key" in j and isinstance(j["key"], dict):
            meta = j["key"].copy()
            # Rename entity_id to asset_id
            if "entity_id" in meta:
                meta["asset_id"] = meta.pop("entity_id")
            for k, v in meta.items():
                df[k] = v

        dfs.append(df)

    if not dfs:
        raise RuntimeError("No valid data frames were created from the folder.")

    return pd.concat(dfs, ignore_index=True)


def create_table_if_not_exists(ch_client, ddl_path: str, table_check_sql: str):
    table_exists = bool(ch_client.query(table_check_sql).result_set)
    if not table_exists:
        with open(ddl_path, 'r') as file:
            ddl = file.read()
        ch_client.command(ddl)
    return not table_exists


def insert_data(ch_client, table_name: str, df: pd.DataFrame):
    ch_client.insert_df(table_name, df)


def main():
    from connections.clickhouse_client import ClickHouseClient

    OWNER = "FlexPwr"
    REPO = "DataEngineeringChallenge"
    PATH = "src/vpp/live_measured_infeed"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    github_api = GitHubAPI(OWNER, REPO, GITHUB_TOKEN)

    df = load_all_files_from_folder(github_api, PATH)
    print("Final shape:", df.shape)
    print(df.columns)
    ch_client = ClickHouseClient().get_client()
    ddl_path = '/home/adminabhi/gitrepo/FlexPwr_DE_Challenge/src/ingestion/ddl/flexpwr_raw.live_measured_infeed.sql'
    table_check_sql = """
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_catalog='flexpwr_raw' 
          AND table_name='live_measured_infeed'
    """

    created = create_table_if_not_exists(ch_client, ddl_path, table_check_sql)
    if created:
        print("Table created.")
    print("Inserting data into ClickHouse...")
    insert_data(ch_client, 'flexpwr_raw.live_measured_infeed', df)
    print("Data inserted successfully.")


if __name__ == "__main__":
    main()
