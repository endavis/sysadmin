import sqlite3
from datetime import datetime

# Adapter to convert datetime to string
def adapt_datetime(dt):
    return dt.isoformat()

# Converter to convert string to datetime
def convert_datetime(s):
    return datetime.fromisoformat(s.decode())

# Register the adapter and converter for specific column names
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("az_maint_not_before", convert_datetime)
sqlite3.register_converter("az_maint_scheduled", convert_datetime)
sqlite3.register_converter("az_maint_started", convert_datetime)
sqlite3.register_converter("az_maint_complete", convert_datetime)
sqlite3.register_converter("node_takeover_complete", convert_datetime)
sqlite3.register_converter("node_reboot_starts", convert_datetime)
sqlite3.register_converter("node_reboot_complete", convert_datetime)
sqlite3.register_converter("node_ready_for_giveback", convert_datetime)
sqlite3.register_converter("node_giveback_starts", convert_datetime)
sqlite3.register_converter("node_giveback_complete", convert_datetime)

class AzEventsDB:
    def __init__(self, config, db_name='azevents.db'):
        db_location = config.db_dir / db_name
        self.conn = sqlite3.connect(db_location, detect_types=sqlite3.PARSE_DECLTYPES)
        self.create_table()

    def create_table(self):
        # Check if the table already exists
        cur = self.conn.cursor()
        cur.execute('''
            SELECT name FROM sqlite_master WHERE type='table' AND name='maintenance_events'
        ''')
        if cur.fetchone() is None:
            # Create the table if it does not exist
            with self.conn:
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS maintenance_events (
                        event_id TEXT PRIMARY KEY,
                        cluster TEXT DEFAULT 'Unknown',
                        node TEXT DEFAULT 'Unknown',
                        type TEXT DEFAULT 'Unknown',
                        az_maint_not_before TEXT,
                        az_maint_scheduled TEXT,
                        az_maint_started TEXT,
                        az_maint_complete TEXT,
                        node_takeover_complete TEXT,
                        node_reboot_starts TEXT,
                        node_reboot_complete TEXT,
                        node_ready_for_giveback TEXT,
                        node_giveback_starts TEXT,
                        node_giveback_complete TEXT
                    )
                ''')

    def upsert_event(self, event):
        # Dynamically create the insert string
        columns = ', '.join(event.keys())
        placeholders = ', '.join(f':{key}' for key in event.keys())
        updates = ', '.join(f'{key}=excluded.{key}' for key in event.keys())

        sql = f'''
            INSERT INTO maintenance_events ({columns})
            VALUES ({placeholders})
            ON CONFLICT(event_id) DO UPDATE SET
            {updates}
        '''

        with self.conn:
            self.conn.execute(sql, event)

    def get_event_by_id(self, event_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM maintenance_events WHERE event_id = ?', (event_id,))
        return cur.fetchone()

    def get_events_by_cluster(self, cluster):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM maintenance_events WHERE cluster = ?', (cluster,))
        return cur.fetchall()

    def get_events_by_node(self, node):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM maintenance_events WHERE node = ?', (node,))
        return cur.fetchall()

    def get_events_between_datetimes(self, field, start_datetime, end_datetime):
        query = f'SELECT * FROM maintenance_events WHERE {field} BETWEEN ? AND ?'
        cur = self.conn.cursor()
        cur.execute(query, (start_datetime, end_datetime))
        return cur.fetchall()

# # Example usage
# db = MaintenanceDB()

# # Upsert an event with missing keys
# event = {
#     'event_id': '2',
#     'cluster': 'cluster2',
#     'node': 'node2',
#     'type': 'type2',
#     'az_maint_not_before': datetime.now(),
#     'az_maint_scheduled': datetime.now(),
#     'az_maint_started': datetime.now(),
#     'az_maint_complete': datetime.now()
# }
# db.upsert_event(event)

# # Get event by id
# print(db.get_event_by_id('2'))

# # Get events by cluster
# print(db.get_events_by_cluster('cluster2'))

# # Get events by node
# print(db.get_events_by_node('node2'))

# # Get events between datetimes
# start_datetime = datetime(2022, 1, 1)
# end_datetime = datetime(2023, 1, 1)
# print(db.get_events_between_datetimes('az_maint_scheduled', start_datetime, end_datetime))
