import os
import re
import pandas as pd
from io import StringIO
from datetime import datetime
from typing import List, Dict, Any
import requests


class GitHubAPI:
    """Wrapper around GitHub API for CSV fetching."""
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

    def download_csv(self, url: str) -> pd.DataFrame:
        r = self.session.get(url, headers=self.headers)
        r.raise_for_status()
        return pd.read_csv(StringIO(r.text))


def load_final_production_data(github_api: GitHubAPI, path: str) -> pd.DataFrame:
    files = github_api.list_dir(path)
    csv_files = [
        f for f in files
        if f.get("type") == "file"
        and f["name"].startswith("final_production")
        and f["name"].endswith(".csv")
    ]

    if not csv_files:
        raise RuntimeError("No matching CSV files found.")

    all_data = []

    for f in csv_files:
        df = github_api.download_csv(f["download_url"])

        if df.shape[1] != 2:
            raise ValueError(f"Unexpected number of columns in {f['name']}")

        # Rename columns
        delivery_col = "delivery_start__utc_"
        asset_col = df.columns[1]
        asset_id = asset_col.replace("__kw_", "")
        asset_id = asset_id.replace("MP-", "")
        asset_id = asset_id.replace("-", "-DE-")

        df = df.rename(columns={
            delivery_col: "delivery_start__utc",
            asset_col: "value"
        })
        df["asset_id"] = asset_id
        df["delivery_start__utc"] = pd.to_datetime(df["delivery_start__utc"], utc=True)
        #df["delivery_start__utc"] = df["delivery_start__utc"].dt.tz
        # Extract year-month-day for CEST (Europe/Berlin) without modifying timestamp
        df["ymd"] = df["delivery_start__utc"].dt.tz_convert("Europe/Berlin").dt.date

        all_data.append(df[["asset_id", "delivery_start__utc", "value", "ymd"]])

    return pd.concat(all_data, ignore_index=True)


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
    PATH = "src/distribution_system_operator"  # <-- Adjust to actual GitHub folder path
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    github_api = GitHubAPI(OWNER, REPO, GITHUB_TOKEN)
    df = load_final_production_data(github_api, PATH)
    print("Data shape:", df.shape)

    ch_client = ClickHouseClient().get_client()
    ddl_path = '/home/adminabhi/gitrepo/FlexPwr_DE_Challenge/src/ingestion/ddl/flexpwr_raw.final_production.sql'
    table_check_sql = """
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_catalog='flexpwr_raw' 
          AND table_name='final_production'
    """

    created = create_table_if_not_exists(ch_client, ddl_path, table_check_sql)
    if created:
        print("Table created.")

    print("Inserting data into ClickHouse...")
    insert_data(ch_client, 'flexpwr_raw.final_production', df)
    print("Data inserted successfully.")


if __name__ == "__main__":
    main()
