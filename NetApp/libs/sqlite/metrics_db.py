import sqlite3
import logging
import pprint
from datetime import datetime

# Adapter to convert datetime to string
def adapt_datetime(dt):
    return dt.isoformat()

# Converter to convert string to datetime
def convert_datetime(s):
    return datetime.fromisoformat(s.decode())

# Register the adapter and converter for specific column names
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

class MetricDB:
    def __init__(self, config, db_name='metrics.db'):
        self.db_location = config.db_dir / db_name
        self.conn = sqlite3.connect(self.db_location, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row  # Enables dictionary-like access        
        # self.create_table()

    def create_table(self, table_name):
        # Check if the table already exists
        cur = self.conn.cursor()
        cur.execute(f'''
            SELECT name FROM sqlite_master WHERE type="table" AND name="{table_name}"
        ''')
        if cur.fetchone() is None:
            # Create the table if it does not exist
            sql = f'''
                    CREATE TABLE IF NOT EXISTS "{table_name}" (
                        timestamp TEXT PRIMARY KEY,
                        read_ops REAL,
                        write_ops REAL,
                        read_latency REAL,
                        write_latency REAL,
                        read_throughput REAL,
                        write_throughput REAL
                    )
                '''
            with self.conn:
                self.conn.execute(sql)

    def upsert_data(self, table_name, data):
        # Dynamically create the insert string
        columns = ', '.join(data.keys())
        placeholders = ', '.join(f':{key}' for key in data.keys())
        updates = ', '.join(f'{key}=excluded.{key}' for key in data.keys())

        sql = f'''
            INSERT INTO "{table_name}" ({columns})
            VALUES ({placeholders})
            ON CONFLICT(timestamp) DO UPDATE SET
            {updates}
        '''

        with self.conn:
            self.conn.execute(sql, data)

    def upsert_many(self, table_name, all_data: list):
        columns = list(all_data[0].keys())
        # pprint.pprint(columns)
        placeholders = ', '.join(f':{key}' for key in columns)
        updates = ', '.join(f'{key}=excluded.{key}' for key in columns)

        sql = f'''
            INSERT INTO "{table_name}" ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(timestamp) DO UPDATE SET
            {updates}
        '''
        with self.conn:
            self.conn.executemany(sql, all_data)

# # Example usage
# db = MaintenanceDB()
