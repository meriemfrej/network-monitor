from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
import subprocess
import speedtest
import psutil
import sqlite3
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Host:
    id: int
    name: str
    ip: str

@dataclass
class Metric:
    id: int
    host: Host
    date: datetime
    
    def calculer(self):
        pass

@dataclass
class Latence(Metric):
    valeur: float
    packets_perdus: int

    def __init__(self, host: Host):
        self.host = host
    
    def calculer(self) -> tuple[float, int]:
        logger.info(f"Calculating latency for host: {self.host.name} ({self.host.ip})")
        try:
            cmd = ['ping', '-n', '4', self.host.ip] # Updated ping command for Windows
            logger.debug(f"Executing command: {' '.join(cmd)}")
            output = subprocess.check_output(cmd).decode(encoding="utf-8", errors="replace").split('\n')
            
            packets_sent = 4
            packets_received = len([line for line in output if 'octets=32' in line]) # Updated packet received parsing
            
            packets_lost = packets_sent - packets_received
            
            for line in output:
                if 'Moyenne' in line: # Updated average latency parsing
                    avg_latency = float(line.split('=')[1].strip().split('ms')[0])
                    logger.info(f"Latency calculation complete. Avg latency: {avg_latency}ms, Packets lost: {packets_lost}")
                    return avg_latency, (packets_lost / packets_sent) * 100
            
            logger.warning("Could not parse ping output for latency information")
            return 0.0, 100.0
            
        except Exception as e:
            logger.error(f"Error calculating latency: {str(e)}")
            return 0.0, 100.0

@dataclass
class BandePassante(Metric):
    upload: float
    download: float

    def __init__(self, host: Host):
        self.host = host
    
    def calculer(self) -> tuple[float, float]:
        logger.info(f"Calculating bandwidth for host: {self.host.name} ({self.host.ip})")
        try:
            st = speedtest.Speedtest()
            logger.info("Starting download speed test")
            download = st.download() / 1_000_000  # Convert to Mbps
            logger.info(f"Download speed: {download:.2f} Mbps")
            
            time.sleep(2)  # Add a 2-second delay to simulate longer operation
            
            logger.info("Starting upload speed test")
            upload = st.upload() / 1_000_000  # Convert to Mbps
            logger.info(f"Upload speed: {upload:.2f} Mbps")
            
            return upload, download
        except Exception as e:
            logger.error(f"Error calculating bandwidth: {str(e)}")
            return 0.0, 0.0

class Database:
    def __init__(self, db_name='network_monitor.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.create_tables()
        logger.info(f"Database initialized: {db_name}")

    def create_tables(self):
        logger.info("Creating database tables if they don't exist")
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS hosts (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS latence (
                    id INTEGER PRIMARY KEY,
                    host_id INTEGER,
                    date TIMESTAMP,
                    valeur REAL,
                    packets_perdus INTEGER,
                    FOREIGN KEY (host_id) REFERENCES hosts (id)
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS bande_passante (
                    id INTEGER PRIMARY KEY,
                    host_id INTEGER,
                    date TIMESTAMP,
                    upload REAL,
                    download REAL,
                    FOREIGN KEY (host_id) REFERENCES hosts (id)
                )
            ''')
        logger.info("Database tables created successfully")

    def add_host(self, name: str, ip: str) -> int:
        logger.info(f"Adding new host: {name} ({ip})")
        with self.conn:
            cursor = self.conn.execute('INSERT INTO hosts (name, ip) VALUES (?, ?)', (name, ip))
            return cursor.lastrowid

    def get_hosts(self) -> List[Host]:
        logger.info("Fetching all hosts from database")
        with self.conn:
            cursor = self.conn.execute('SELECT id, name, ip FROM hosts')
            return [Host(id=row[0], name=row[1], ip=row[2]) for row in cursor.fetchall()]

    def add_latence(self, host_id: int, date: datetime, valeur: float, packets_perdus: int):
        logger.info(f"Adding latency data for host_id {host_id}: {valeur}ms, {packets_perdus}% packets lost")
        with self.conn:
            self.conn.execute('''
                INSERT INTO latence (host_id, date, valeur, packets_perdus)
                VALUES (?, ?, ?, ?)
            ''', (host_id, date, valeur, packets_perdus))

    def add_bande_passante(self, host_id: int, date: datetime, upload: float, download: float):
        logger.info(f"Adding bandwidth data for host_id {host_id}: Upload {upload:.2f} Mbps, Download {download:.2f} Mbps")
        with self.conn:
            self.conn.execute('''
                INSERT INTO bande_passante (host_id, date, upload, download)
                VALUES (?, ?, ?, ?)
            ''', (host_id, date, upload, download))

    def close(self):
        logger.info("Closing database connection")
        self.conn.close()

    def get_host_id(self, name: str) -> int:
        logger.info(f"Fetching host ID for name: {name}")
        with self.conn:
            cursor = self.conn.execute('SELECT id FROM hosts WHERE name = ?', (name,))
            result = cursor.fetchone()
            if result:
                logger.info(f"Host ID found: {result[0]}")
                return result[0]
            else:
                logger.warning(f"No host found with name: {name}")
                return None

    def get_latency_history(self, host_id: int) -> List[tuple]:
        logger.info(f"Fetching latency history for host_id: {host_id}")
        with self.conn:
            cursor = self.conn.execute('''
                SELECT date, valeur, packets_perdus
                FROM latence
                WHERE host_id = ?
                ORDER BY date DESC
            ''', (host_id,))
            return cursor.fetchall()

    def get_bandwidth_history(self, host_id: int) -> List[tuple]:
        logger.info(f"Fetching bandwidth history for host_id: {host_id}")
        with self.conn:
            cursor = self.conn.execute('''
                SELECT date, upload, download
                FROM bande_passante
                WHERE host_id = ?
                ORDER BY date DESC
            ''', (host_id,))
            return cursor.fetchall()

    def update_host(self, old_name: str, new_name: str, new_ip: str):
        logger.info(f"Updating host: {old_name} -> {new_name}, {new_ip}")
        with self.conn:
            self.conn.execute('''
                UPDATE hosts
                SET name = ?, ip = ?
                WHERE name = ?
            ''', (new_name, new_ip, old_name))

    def delete_host(self, name: str):
        logger.info(f"Deleting host: {name}")
        with self.conn:
            host_id = self.get_host_id(name)
            if host_id:
                self.conn.execute('DELETE FROM hosts WHERE id = ?', (host_id,))
                self.conn.execute('DELETE FROM latence WHERE host_id = ?', (host_id,))
                self.conn.execute('DELETE FROM bande_passante WHERE host_id = ?', (host_id,))
                logger.info(f"Host and associated data deleted for {name}")
            else:
                logger.warning(f"No host found with name: {name}")

