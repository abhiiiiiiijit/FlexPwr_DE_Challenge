import pendulum
import clickhouse_connect
from client import get_forecast
import json

# ClickHouse connection
ch_client = clickhouse_connect.get_client(
    host='eay8wn9jhw.eu-central-1.aws.clickhouse.cloud',
    user='default',
    password='2~i795k.Qnixc',
    secure=True
)

# Step 1: Get all asset_ids
rows = ch_client.query("SELECT DISTINCT asset_id FROM flexpwr_raw.technical_data").result_set
print(rows)
asset_ids = [row[0] for row in rows]

# Fixed forecast date
forecast_version = pendulum.datetime(2025, 6, 8, 11, 45, tz="Europe/Berlin") # latest forecast for all assets for this date
ymd = forecast_version.date()  # Convert to date for ClickHouse
# Accumulate all forecasts in one list
bulk_insert_data = []

for asset_id in asset_ids:
    try:
        forecast = get_forecast(asset_id=asset_id, version=forecast_version)
        forecast = json.loads(forecast) # Convert to dict if needed
        col_ids = forecast["column_ids"]
        

        # Transpose values to get rows: (start, end, version, power)
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

# Step 2: Bulk insert into ClickHouse
if bulk_insert_data:
    ch_client.insert('flexpwr_raw.asset_forecast', bulk_insert_data, column_names=['asset_id', 'type_id', 'start', 'end', 'version', 'power', 'ymd'])

else:
    print("No data to insert.")











# from client import get_forecast
# import pendulum

# f = get_forecast(
#     asset_id="WND-DE-003",
#     version=pendulum.datetime(2025, 8, 9, 8, 30, tz="Europe/Berlin"),
# )

# print(f"Forecast for asset WND-DE-003 at 2025-06-08T08:15:00+02:00: {f}")

