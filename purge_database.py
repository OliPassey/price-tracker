#!/usr/bin/env python3
"""
Simple script to purge all price data from the database
This will reset the database so the next scrape acts as the first one
"""

import sqlite3
import os
from src.config import Config

def purge_database():
    """Purge all data from the price tracker database."""
    config = Config()
    db_path = config.database_path
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist. Nothing to purge.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in database.")
            conn.close()
            return
        
        print(f"Found {len(tables)} tables in database:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} records")
        
        # Confirm purge
        response = input("\nDo you want to purge all data? (yes/no): ").lower().strip()
        
        if response in ['yes', 'y']:
            # Delete all data from all tables
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DELETE FROM {table_name}")
                print(f"Purged all data from {table_name}")
            
            conn.commit()
            print("\n✅ Database purged successfully!")
            print("The next scrape will act as the first one and log all prices.")
        else:
            print("Purge cancelled.")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    purge_database()
