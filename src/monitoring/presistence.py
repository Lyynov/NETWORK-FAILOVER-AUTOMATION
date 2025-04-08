"""
Modul untuk penyimpanan data metrik jaringan.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from config.settings import DB_PATH

# Set up logging
logger = logging.getLogger(__name__)

class MetricsPersistence:
    """Persistence manager for network metrics."""
    
    def __init__(self, db_path=None):
        """
        Initialize metrics persistence.
        
        Args:
            db_path (str, optional): Path to SQLite database file
        """
        self.db_path = db_path or DB_PATH
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database and tables exist."""
        try:
            # membuat direktori ketika belum tersedia
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create metrics table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interface_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interface TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    status TEXT NOT NULL,
                    latency REAL NOT NULL,
                    packet_loss REAL NOT NULL,
                    timestamp_readable TEXT NOT NULL
                )
            ''')
            
            # membuat index pada timestamp dan metric
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_interface_timestamp 
                ON interface_metrics (interface, timestamp)
            ''')
            
            # membuat tabel kegiatan failover
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS failover_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    from_interface TEXT NOT NULL,
                    to_interface TEXT NOT NULL,
                    reason TEXT,
                    timestamp_readable TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def store_metrics(self, metrics):
        """
        Store interface metrics in the database.
        
        Args:
            metrics (dict): Interface metrics dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Format timestamp for readability
            timestamp_readable = datetime.fromtimestamp(
                metrics['timestamp']
            ).strftime('%Y-%m-%d %H:%M:%S')
            
            # Insert metrics
            cursor.execute('''
                INSERT INTO interface_metrics 
                (interface, timestamp, status, latency, packet_loss, timestamp_readable)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metrics['interface'],
                metrics['timestamp