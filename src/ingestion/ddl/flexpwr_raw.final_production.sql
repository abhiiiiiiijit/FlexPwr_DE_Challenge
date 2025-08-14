CREATE TABLE IF NOT EXISTS flexpwr_raw.final_production (
    asset_id String,
    delivery_start__utc DateTime,
    "value" Float64,
    ymd Date DEFAULT toDate(toTimeZone(now(), 'Europe/Berlin') ),
    created_by String DEFAULT currentUser() ,
    created_at DateTime DEFAULT toTimeZone(now(), 'Europe/Berlin') 

)
ENGINE = MergeTree()
PARTITION BY (ymd)
ORDER BY (asset_id, delivery_start__utc);