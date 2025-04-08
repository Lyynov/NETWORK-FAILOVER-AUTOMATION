"""
Modul untuk komunikasi dengan router MikroTik.
"""
import logging
from librouteros import connect
from librouteros.login import plain
from librouteros.exceptions import ConnectionError, LoginError

# Set up logging
logger = logging.getLogger(__name__)

class MikrotikClient:
    """Client for communicating with MikroTik routers."""
    
    def __init__(self, host, username, password, port=8728, use_ssl=False, timeout=10):
        """
        Initialize MikroTik client.
        
        Args:
            host (str): Router IP address or hostname
            username (str): API username
            password (str): API password
            port (int): API port (default: 8728)
            use_ssl (bool): Use SSL for API connection
            timeout (int): Connection timeout in seconds
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.api = None
    
    def connect(self):
        """
        Connect to the MikroTik router.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.api = connect(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                ssl=self.use_ssl,
                timeout=self.timeout,
                login_method=plain
            )
            logger.info(f"Connected to MikroTik router at {self.host}")
            return True
        except ConnectionError as e:
            logger.error(f"Failed to connect to MikroTik router: {e}")
            return False
        except LoginError as e:
            logger.error(f"Failed to authenticate with MikroTik router: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MikroTik router: {e}")
            return False
    
    def disconnect(self):
        """Close the connection to the router."""
        if self.api:
            self.api.close()
            self.api = None
            logger.info("Disconnected from MikroTik router")
    
    def get_interfaces(self):
        """
        Get list of interfaces from the router.
        
        Returns:
            list: List of interface dictionaries
        """
        if not self.api:
            if not self.connect():
                return []
        
        try:
            # ,mengambil data seluruh interface
            interfaces_path = self.api.path('interface')
            interfaces = list(interfaces_path)
            return interfaces
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")
            return []
    
    def get_interface_status(self, interface_name):
        """
        Get status of a specific interface.
        
        Args:
            interface_name (str): Name of the interface
            
        Returns:
            dict: Interface status dictionary or None if not found
        """
        interfaces = self.get_interfaces()
        for interface in interfaces:
            if interface.get('name') == interface_name:
                return interface
        return None
    
    def check_interface_connectivity(self, interface_name, target='8.8.8.8', count=5):
        """
        Check connectivity of an interface by running a ping test.
        
        Args:
            interface_name (str): Name of the interface
            target (str): IP address to ping
            count (int): Number of pings to send
            
        Returns:
            dict: Dictionary with ping results or None on error
        """
        if not self.api:
            if not self.connect():
                return None
        
        try:
            # command ping ke mikrotik
            ping_cmd = self.api.path('ping')
            
            # menjalankan ping ke mikrotik beserta hasil
            ping_result = ping_cmd(**{
                'address': target,
                'interface': interface_name,
                'count': count
            })
            
            # hasil proses
            results = list(ping_result)
            
            # menghitung rata2 statistik
            sent = count
            received = sum(1 for r in results if 'time' in r)
            packet_loss = ((sent - received) / sent) * 100 if sent > 0 else 0
            
            times = [float(r.get('time', 0)) for r in results if 'time' in r]
            avg_time = sum(times) / len(times) if times else float('inf')
            
            return {
                'interface': interface_name,
                'target': target,
                'sent': sent,
                'received': received,
                'packet_loss': packet_loss,
                'avg_latency': avg_time
            }
            
        except Exception as e:
            logger.error(f"Error checking interface connectivity: {e}")
            return None
    
    def update_routing_priority(self, interface_name, new_distance=1):
        """
        Update routing priority for an interface.
        
        Args:
            interface_name (str): Name of the interface to update
            new_distance (int): New routing distance (lower = higher priority)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.api:
            if not self.connect():
                return False
        
        try:
            # mencari default route pada masing2 interface
            ip_route = self.api.path('ip/route')
            routes = list(ip_route)
            
            target_routes = []
            for route in routes:
                if route.get('gateway') and interface_name in route.get('gateway', ''):
                    target_routes.append(route)
            
            if not target_routes:
                logger.warning(f"No routes found for interface {interface_name}")
                return False
            
            # Update the distance for each matching route
            for route in target_routes:
                ip_route.update(
                    **{
                        '.id': route['.id'],
                        'distance': str(new_distance)
                    }
                )
            
            logger.info(f"Updated routing priority for {interface_name} to {new_distance}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating routing priority: {e}")
            return False
    
    def execute_script(self, script_name):
        """
        Execute a predefined script on the router.
        
        Args:
            script_name (str): Name of the script to execute
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.api:
            if not self.connect():
                return False
        
        try:
            #jalankan script
            system_script = self.api.path('system/script')
            result = system_script.run(name=script_name)
            
            logger.info(f"Executed script '{script_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return False