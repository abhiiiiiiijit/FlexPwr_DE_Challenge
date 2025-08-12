import os
import re
import json
import requests
import pandas as pd
from datetime import datetime
from connections.clickhouse_client import ClickHouseClient



# --- Config ---
OWNER = "FlexPwr"
REPO = "DataEngineeringChallenge"
PATH = "src/vpp/technical_data"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional

headers = {}
if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

# --- Helpers ---
TS_RE = re.compile(r"technical_data_(\d{4}-\d{2}-\d{2}T\d{6}Z)\.json", re.I)

def list_dir(owner, repo, path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def find_latest_file(files):
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

def extract_record_list(j):
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

def load_latest_technical_data_df():
    files = list_dir(OWNER, REPO, PATH)
    latest_ts, latest_url, latest_name = find_latest_file(files)
    print(f"Downloading latest: {latest_name} ({latest_ts.isoformat()})")
    r = requests.get(latest_url, headers=headers)
    r.raise_for_status()
    j = r.json()
    records = extract_record_list(j)

    # Convert to DataFrame without flattening nested dicts
    df = pd.DataFrame(records)

    # Ensure nested dict columns are stored as JSON strings (optional, for ClickHouse)
    for col in df.columns:
        if isinstance(df[col].iloc[0], dict):
            df[col] = df[col].apply(json.dumps)

    df['ymd'] = pd.to_datetime(latest_ts).date()  # Add date column

    return df

def create_table_tech_data(ch_client):
    # Read SQL file
    with open('src/ingestion/ddl/flexpwr_raw.technical_data.sql', 'r') as file:
        raw_tech_ddl = file.read()
    ch_client.command(raw_tech_ddl)


# --- Run ---
if __name__ == "__main__":
    df = load_latest_technical_data_df()
    print("Shape:", df.shape)


    ch_client = ClickHouseClient().get_client()


    table_exists = bool(ch_client.query('''SELECT 1 
                                        FROM information_schema.tables 
                                        where table_catalog='flexpwr_raw' 
                                        and table_name='technical_data''').result_set)
    print("Table exists:", table_exists)
    if not table_exists:
        create_table_tech_data(ch_client)  
    
    print("Inserting data into ClickHouse...")
    table_name = 'flexpwr_raw.technical_data'  #
    ch_client.insert_df(table_name, df)
    print("Data inserted successfully.")     


