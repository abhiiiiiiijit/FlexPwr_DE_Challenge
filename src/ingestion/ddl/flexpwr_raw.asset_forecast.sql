CREATE TABLE flexpwr_raw.asset_forecast (
    asset_id String,
    type_id String,
    start UInt64,
    end UInt64,
    version UInt64,
    power Float64,
    ymd Date DEFAULT toDate(now())
)
ENGINE = MergeTree()
PARTITION BY ymd
ORDER BY (asset_id, version, start)