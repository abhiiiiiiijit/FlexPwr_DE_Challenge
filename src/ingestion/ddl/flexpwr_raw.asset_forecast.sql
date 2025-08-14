CREATE TABLE IF NOT EXISTS flexpwr_raw.asset_forecast (
    asset_id String,
    type_id String,
    start UInt64,
    end UInt64,
    version UInt64,
    power Float64,
    ymd Date DEFAULT toDate(toTimeZone(now(), 'Europe/Berlin') ),
    created_by String DEFAULT currentUser() ,
    created_at DateTime DEFAULT toTimeZone(now(), 'Europe/Berlin') 
)
ENGINE = MergeTree()
PARTITION BY ymd
ORDER BY (asset_id, version, start)
PRIMARY KEY (asset_id, version, start);