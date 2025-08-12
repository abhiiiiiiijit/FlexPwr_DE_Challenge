CREATE TABLE IF NOT EXISTS flexpwr_raw.technical_data (
        asset_id String,
        name String,
        type String,
        location String,
        technical_attributes String,
        status String,
        owner String,
        ymd Date DEFAULT toDate(now())
    )
    ENGINE = MergeTree()
    PARTITION BY ymd
    ORDER BY (asset_id, ymd)
    PRIMARY KEY (asset_id, ymd);