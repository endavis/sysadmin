
from libs.config import Config
from libs.parseargs import argp
from libs.log import setup_logger

import sqlite3
import pandas as pd
import pathlib
import logging

setup_logger()

script_name = pathlib.Path(__file__).stem

def save_database(database_file, output_file):
    # Connect to your SQLite database
    conn = sqlite3.connect(database_file)

    # Read the table into a pandas DataFrame
    df = pd.read_sql_query("SELECT * FROM maintenance_events", conn)

    # Export to Excel
    df.to_excel(output_file, index=False, engine='xlsxwriter')  # or use engine='xlsxwriter'


if __name__ == '__main__':
    args = argp(script_name=script_name ,description="gather volume and cluster stats, provisioned size and savings if changing to 80% and 90% autosize thresholds", parse=False)
    args.parser.add_argument('-i', '--inputfile', type=str, help="inputfile", default="", required=True)
    args.parse()

    config = Config(args.config_dir, args.output_dir)

    save_database(args.inputfile, f'{args.output_dir}/azevents.xlsx')
