import os
import re
import json
import requests
import pandas as pd
from datetime import datetime
import clickhouse_connect

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

    # Parse date fields if present
    if "technical_attributes" in df.columns:
        # If commissioning_date is inside technical_attributes, leave it as is inside JSON
        pass
    if "commissioning_date" in df.columns:
        df["commissioning_date"] = pd.to_datetime(df["commissioning_date"], errors="coerce")

    return df

def create_table_tech_data(client):
    client.command("""
        CREATE TABLE IF NOT EXISTS flexpwr.technical_data (
            asset_id String,
            name String,
            type String,
            location String,
            technical_attributes String,
            status String,
            owner String
        )
        ENGINE = MergeTree()
        ORDER BY (asset_id);
    """)
    # client.command("""
    #     CREATE TABLE IF NOT EXISTS flexpwr.technical_data (
    #         asset_id String,
    #         name String,
    #         type String,
    #         location Map(String, String),
    #         technical_attributes Map(String, String),
    #         status String,
    #         owner Map(String, String)
    #     )
    #     ENGINE = MergeTree()
    #     ORDER BY (asset_id);
    # """)


# --- Run ---
if __name__ == "__main__":
    df = load_latest_technical_data_df()
    print("Shape:", df.shape)

    # pd.set_option('display.max_rows', none)      # show all rows
    # pd.set_option('display.max_columns', none)   # show all columns
    # pd.set_option('display.width', none)         # auto-detect width to avoid wrapping
    # pd.set_option('display.max_colwidth', none)
    # print(df.head())

    client = clickhouse_connect.get_client(
        host='eay8wn9jhw.eu-central-1.aws.clickhouse.cloud',
        user='default',
        password='2~i795k.Qnixc',
        secure=True
    )


    table_exists = bool(client.query("SELECT 1 FROM information_schema.tables where table_catalog='flexpwr' and table_name='technical_data'").result_set)
    print("Table exists:", table_exists)
    if not table_exists:
        create_table_tech_data(client)  
    
    print("Inserting data into ClickHouse...")
    # Insert data from Pandas DataFrame
    # rows = list(df.itertuples(index=False, name=None))
    # print(rows)
    # client.command(
    #     f'''INSERT INTO flexpwr.technical_data
    #     (asset_id, name, type, location, technical_attributes, status, owner)
    #       VALUES''',
    #     df.to_dict('records')
    # )
    table_name = 'flexpwr.technical_data'  #
    client.insert_df(table_name, df)
    print("Data inserted successfully.")    


