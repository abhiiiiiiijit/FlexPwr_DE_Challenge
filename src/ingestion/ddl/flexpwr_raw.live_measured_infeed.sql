CREATE TABLE IF NOT EXISTS flexpwr_raw.live_measured_infeed (
    asset_id String,
    type_id String,
    "timestamp" UInt64,
    "value" Float64,
    quality Float64,
    ymd Date DEFAULT toDate(toTimeZone(now(), 'Europe/Berlin') ),
    created_by String DEFAULT currentUser() ,
    created_at DateTime DEFAULT toTimeZone(now(), 'Europe/Berlin') 

)
ENGINE = MergeTree()
PARTITION BY (ymd)
ORDER BY (asset_id, "timestamp")
PRIMARY KEY (asset_id, "timestamp");