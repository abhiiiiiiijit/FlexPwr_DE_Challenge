import os
import clickhouse_connect


class ClickHouseClient:

    def __init__(self):
        self.client = clickhouse_connect.get_client(
            host=os.getenv("CH_HOST"),
            user=os.getenv("CH_USER"),
            password=os.getenv("CH_PASSWORD"),
            secure=True
        )

    def get_client(self):
        return self.client



