import argparse
import json
import pendulum
from client import get_forecast
from connections.clickhouse_client import ClickHouseClient


def parse_args():
    parser = argparse.ArgumentParser(
        description="Insert asset forecasts into ClickHouse."
    )
    parser.add_argument(
        "--forecast_version",
        type=str,
        help=(
            "Forecast version timestamp in ISO 8601 format "
            "(e.g., 2025-06-08T11:45). Defaults to current time in Europe/Berlin."
        ),
    )
    return parser.parse_args()


def get_forecast_version(version_str: str | None) -> pendulum.DateTime:
    if version_str:
        return pendulum.parse(version_str, tz="Europe/Berlin")
    version = pendulum.now("Europe/Berlin")
    version = version.format("YYYY-MM-DDTHH:mm")
    return pendulum.parse(version, tz="Europe/Berlin")


def fetch_asset_ids(ch_client) -> list[str]:
    rows = ch_client.query(
        "SELECT DISTINCT asset_id FROM flexpwr_raw.technical_data"
    ).result_set
    return [row[0] for row in rows]

def create_table_if_not_exists(ch_client, ddl_path: str, table_check_sql: str):
    table_exists = bool(
        ch_client.query(table_check_sql).result_set
    )
    if not table_exists:
        with open(ddl_path, 'r') as file:
            ddl = file.read()
        ch_client.command(ddl)
    return not table_exists  # Returns True if table was created

def build_bulk_insert_data(asset_ids, forecast_version, ymd) -> list[tuple]:
    bulk_insert_data = []
    for asset_id in asset_ids:
        try:
            forecast = get_forecast(asset_id=asset_id, version=forecast_version)
            forecast = json.loads(forecast)
            col_ids = forecast["column_ids"]
            values_list = list(zip(*forecast["values"]))

            for row in values_list:
                data_dict = dict(zip(col_ids, row))
                bulk_insert_data.append((
                    forecast["key"]["asset_id"],
                    forecast["key"]["type_id"],
                    int(data_dict["start"]),
                    int(data_dict["end"]),
                    int(data_dict["version"]),
                    float(data_dict["power"]),
                    ymd
                ))

            print(f"Processed forecast for {asset_id} ({len(values_list)} rows)")

        except Exception as e:
            print(f"Error processing {asset_id}: {e}")

    return bulk_insert_data


def insert_forecasts(ch_client, bulk_insert_data):
    if bulk_insert_data:
        ch_client.insert(
            'flexpwr_raw.asset_forecast',
            bulk_insert_data,
            column_names=['asset_id', 'type_id', 'start', 'end', 'version', 'power', 'ymd']
        )
    else:
        print("No data to insert.")


def main():
    args = parse_args()
    forecast_version = get_forecast_version(args.forecast_version)
    ymd = forecast_version.date()

    ch_client = ClickHouseClient().get_client()
    asset_ids = fetch_asset_ids(ch_client)
    ddl_path = '/home/adminabhi/gitrepo/FlexPwr_DE_Challenge/src/ingestion/ddl/flexpwr_raw.asset_forecast.sql'
    table_check_sql = """
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_catalog='flexpwr_raw' 
          AND table_name='asset_forecast'
    """

    created = create_table_if_not_exists(ch_client, ddl_path, table_check_sql)
    if created:
        print("Table created.")

    bulk_insert_data = build_bulk_insert_data(asset_ids, forecast_version, ymd)
    insert_forecasts(ch_client, bulk_insert_data)


if __name__ == "__main__":
    main()
