import sqlite3
import os
from datetime import datetime

# Adapter to convert datetime to string
def adapt_datetime(dt):
    return dt.isoformat()

# Converter to convert string to datetime
def convert_datetime(s):
    return datetime.fromisoformat(s.decode())

# Register the adapter and converter for specific column names
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("time", convert_datetime)

class EmsEventsDB:
    def __init__(self, config, db_name='ems_events.db'):
        db_dir = config.db_dir / 'emsevents'
        os.makedirs(db_dir, exist_ok=True)
        db_location = db_dir / db_name
        if os.path.exists(db_location):
            os.remove(db_location)
        self.conn = sqlite3.connect(db_location, detect_types=sqlite3.PARSE_DECLTYPES)
        self.create_table()

    def create_table(self):
        # Check if the table already exists
        cur = self.conn.cursor()
        cur.execute('''
            SELECT name FROM sqlite_master WHERE type='table' AND name='ems_events'
        ''')
        if cur.fetchone() is None:
            # Create the table if it does not exist
            with self.conn:
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS ems_events (
                        event_id TEXT,
                        cluster TEXT DEFAULT 'Unknown',
                        node TEXT DEFAULT 'Unknown',
                        time TEXT,
                        event TEXT DEFAULT 'Unknown',
                        severity TEXT DEFAULT 'Unknown',
                        message TEXT DEFAULT 'Unknown'
                    )
                ''')

    def insert_event(self, event):
        # Dynamically create the insert string
        columns = ', '.join(event.keys())
        placeholders = ', '.join(f':{key}' for key in event.keys())

        sql = f'''
            INSERT INTO ems_events ({columns})
            VALUES ({placeholders})
        '''

        with self.conn:
            self.conn.execute(sql, event)

    def get_events_by_node(self, node):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM ems_events WHERE node = ?', (node,))
        return cur.fetchall()

    def get_events_between_datetimes(self, start_datetime, end_datetime):
        query = 'SELECT * FROM ems_events WHERE time BETWEEN ? AND ?'
        cur = self.conn.cursor()
        cur.execute(query, (start_datetime, end_datetime))
        return cur.fetchall()

# # Example usage
# db = EmsEventsDB()

# # Upsert an event with missing keys
# event = {
#     'event_id': '1',
#     'cluster': 'cluster1',
#     'node': 'node1',
#     'time': datetime.now(),
#     'event': 'event1',
#     'severity': 'high',
#     'message': 'This is a test message'
# }
# db.upsert_event(event)

# # Get event by id
# print(db.get_event_by_id('1'))

# # Get events by node
# print(db.get_events_by_node('node1'))

# # Get events between datetimes
# start_datetime = datetime(2022, 1, 1)
# end_datetime = datetime(2023, 1, 1)
# print(db.get_events_between_datetimes(start_datetime, end_datetime))
