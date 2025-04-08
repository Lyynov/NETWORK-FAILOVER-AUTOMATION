"""
Konfigurasi aplikasi utama.
"""
import os
from dotenv import load_dotenv

# Load environment variables dari env.file
load_dotenv()

# setting aplikasi
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
APP_NAME = "Network Failover Automation"
VERSION = "0.1.0"

# koneksi ke router
ROUTER_HOST = os.getenv('ROUTER_HOST', '192.168.88.1')
ROUTER_USER = os.getenv('ROUTER_USER', 'admin')
ROUTER_PASSWORD = os.getenv('ROUTER_PASSWORD', '')

# konektivitas database metrics
DB_PATH = os.getenv('DB_PATH', 'data/metrics.db')

# Dashboard settings
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8080'))

# AI Model settings
MODEL_PATH = os.getenv('MODEL_PATH', 'models/failover_predictor.pkl')
TRAINING_DAYS = int(os.getenv('TRAINING_DAYS', '7'))  # Days of data for training

# memebuat direktori jika database tidak ada
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)