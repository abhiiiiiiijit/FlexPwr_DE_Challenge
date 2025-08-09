# Data Ingestion Script README

This Python script automates the process of fetching the latest technical data JSON file from a GitHub repository, processing it into a Pandas DataFrame, and ingesting it into a ClickHouse database.

## Overview
- **Purpose**: Fetches and processes technical data from the GitHub repository `FlexPwr/DataEngineeringChallenge` and inserts it into a ClickHouse database table (`flexpwr.technical_data`).
- **Source**: Retrieves JSON files from the repository path `src/vpp/technical_data`.
- **Script Path**: The script is located at `src/ingestion/ingest_tech_details.py`.
- **Schedule**: A new file is created daily at the source between 12:00 and 13:00. It is recommended to schedule the script to run after 13:00 to ensure the latest file is available.

## Prerequisites
- Python 3.x
- Poetry for dependency management
- Required Python packages: `requests`, `pandas`, `clickhouse_connect`
- Access to a ClickHouse database (cloud or local instance)

## Setup
1. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Configure ClickHouse connection details in the script (host, user, password).

## Usage
Run the script manually using Poetry:
```bash
python3 src/ingestion/ingest_tech_details.py
```

### Orchestration
To automate daily ingestion, you can schedule the script to run after 13:00 (e.g., 13:30) using either a cron job or Apache Airflow.

- **Cron Job**: Schedule the script with a crontab entry:
  ```bash
  30 13 * * * /path/to/poetry run python /path/to/src/ingestion/ingest_tech_details.py
  ```
  This runs the script daily at 13:30, after the new file is available between 12:00–13:00.


## Functionality
1. **Fetch Files**: Queries the GitHub API to list files in the specified repository path.
2. **Identify Latest File**: Uses a regex pattern to find JSON files with timestamps and selects the most recent one.
3. **Process Data**: Downloads the latest JSON file, extracts the list of records, and converts it to a Pandas DataFrame.
4. **Database Integration**:
   - Checks if the `flexpwr.technical_data` table exists in ClickHouse.
   - Creates the table if it doesn't exist, with a `MergeTree` engine partitioned by date (`ymd`).
   - Inserts the DataFrame into the table, converting nested dictionaries to JSON strings if needed.

## Table Schema
The ClickHouse table `flexpwr.technical_data` has the following schema:
- `asset_id`: String
- `name`: String
- `type`: String
- `location`: String
- `technical_attributes`: String (JSON string for nested data)
- `status`: String
- `owner`: String
- `ymd`: Date (partition key, defaults to current date)

## Notes
- Ensure the ClickHouse connection details (host, user, password) are secure and not hardcoded in production.
- The script assumes the JSON file contains a list of records (or a dictionary with a list under keys like `assets`, `data`, `items`, or `results`).