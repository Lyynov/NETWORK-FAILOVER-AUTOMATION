"""
Modul untuk pengumpulan metrik jaringan.
"""
import logging
import time
import threading
import schedule
from datetime import datetime
from config.router_config import THRESHOLDS

# Set up log
logger = logging.getLogger(__name__)

class NetworkMonitor:
    """Monitor for collecting network metrics."""
    
    def __init__(self, interface_manager, persistence=None):
        """
        Initialize network monitor.
        
        Args:
            interface_manager (InterfaceManager): Interface manager instance
            persistence (object, optional): Persistence module for storing metrics
        """
        self.interface_manager = interface_manager
        self.persistence = persistence
        self.metrics_history = {}
        self.is_running = False
        self.monitor_thread = None
        self.consecutive_failures = {}
    
    def start_monitoring(self, interval=None):
        """
        Start the monitoring process in a separate thread.
        
        Args:
            interval (int, optional): Monitoring interval in seconds
        """
        if interval is None:
            interval = THRESHOLDS['check_interval']
        
        if self.is_running:
            logger.warning("Monitoring is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"Network monitoring started with interval of {interval} seconds")
    
    def stop_monitoring(self):
        """Stop the monitoring process."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Network monitoring stopped")
    
    def _monitoring_loop(self, interval):
        """
        Main monitoring loop.
        
        Args:
            interval (int): Monitoring interval in seconds
        """
        while self.is_running:
            try:
                # mendapatkan metric
                metrics = self.collect_metrics()
                
                # Process metrics
                self.process_metrics(metrics)
                
                # Break sampai proses selanjutnya
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def collect_metrics(self):
        """
        Collect metrics from all interfaces.
        
        Returns:
            dict: Dictionary with interface metrics
        """
        metrics = self.interface_manager.check_interfaces()
        
        # menyimpan metric pada history
        timestamp = time.time()
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        for interface, interface_metrics in metrics.items():
            if interface not in self.metrics_history:
                self.metrics_history[interface] = []
            
            # menambahkan timestamp jika belum tersedia
            if 'timestamp' not in interface_metrics:
                interface_metrics['timestamp'] = timestamp
            
            # menambahkan ke history
            self.metrics_history[interface].append(interface_metrics)
            
            # menjaga ukuran history tidak lebih dari 1mb
            if len(self.metrics_history[interface]) > 1000:
                self.metrics_history[interface] = self.metrics_history[interface][-1000:]
            
            # menyimpan file pada presistence
            if self.persistence:
                self.persistence.store_metrics(interface_metrics)
            
            # Log metrics
            logger.debug(
                f"[{formatted_time}] Interface {interface}: "
                f"latency={interface_metrics['latency']:.2f}ms, "
                f"packet_loss={interface_metrics['packet_loss']:.2f}%"
            )
        
        return metrics
    
    def process_metrics(self, metrics):
        """
Proses metrik dan tentukan apakah failover diperlukan.

Argumen:
metrice (dict): Kamus dengan metrice interface
"""
        # lacak kegagalan berturut"
        for interface, interface_metrics in metrics.items():
            is_healthy = self.interface_manager.is_interface_healthy(interface_metrics)
            
            if interface not in self.consecutive_failures:
                self.consecutive_failures[interface] = 0
            
            if not is_healthy:
                self.consecutive_failures[interface] += 1
                logger.warning(
                    f"Interface {interface} failure #{self.consecutive_failures[interface]}: "
                    f"latency={interface_metrics['latency']:.2f}ms, "
                    f"packet_loss={interface_metrics['packet_loss']:.2f}%"
                )
            else:
                # Reset counter ketika interface aman
                if self.consecutive_failures[interface] > 0:
                    logger.info(f"Interface {interface} is healthy again")
                    self.consecutive_failures[interface] = 0
        
        # Periksa apakah interface aktif saat ini memiliki cukup banyak kegagalan berturut-turut
        current_active = self.interface_manager.current_active
        if (current_active in self.consecutive_failures and 
            self.consecutive_failures[current_active] >= THRESHOLDS['consecutive_failures']):
            
            # evaluasi failover dibutuhkan
            need_failover, target_interface = self.interface_manager.evaluate_failover_need(metrics)
            
            if need_failover and target_interface != current_active:
                self.interface_manager.perform_failover(current_active, target_interface)
                # reset kegagalan ketika failover telah diterapkan
                self.consecutive_failures[current_active] = 0
    
    def get_latest_metrics(self):
        """
        Get the latest collected metrics for all interfaces.
        
        Returns:
            dict: Dictionary with latest metrics per interface
        """
        latest_metrics = {}
        
        for interface, history in self.metrics_history.items():
            if history:
                latest_metrics[interface] = history[-1]
        
        return latest_metrics
    
    def get_metrics_history(self, interface=None, limit=100):
        """
        Get historical metrics for an interface.
        
        Args:
            interface (str, optional): Interface name or None for all interfaces
            limit (int, optional): Maximum number of records to return
            
        Returns:
            dict or list: Dictionary with interface histories or list for single interface
        """
        if interface:
            history = self.metrics_history.get(interface, [])
            return history[-limit:] if history else []
        
        # return history semua interface
        result = {}
        for iface, history in self.metrics_history.items():
            result[iface] = history[-limit:] if history else []
        
        return result