#!/bin/bash
export PYTHONPATH=/home/adminabhi/gitrepo/FlexPwr_DE_Challenge
export CH_HOST="eay8wn9jhw.eu-central-1.aws.clickhouse.cloud"
export CH_USER="default"
export CH_PASSWORD="2~i795k.Qnixc"

/root/.cache/pypoetry/virtualenvs/flexpwr-de-challenge-XlOLxTpd-py3.10/bin/python /home/adminabhi/gitrepo/FlexPwr_DE_Challenge/src/ingestion/ingest_asset_forecast.py
