"""
AI Healthcare Map with Gorilla LLM Integration
This script integrates Gorilla LLM to process natural language queries
and generate API calls for healthcare map functionality.
Uses SQL database for flexible attribute storage.jhgchjv
Can also run as a Flask server to serve the frontend HTML interface.
"""

import requests
import json
import sqlite3
import os
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager
import logging

# Try to import Flask (optional for server mode)
try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default API Key (can be overridden by environment variable or config)
DEFAULT_API_KEY = "hk_mhgld8wp9b734af8e66639100c921dc5d74a881538baac51eb498103131a55271c082e50"


def get_api_key(source: Optional[str] = None) -> Optional[str]:
    """
    Fetch API key from various sources in priority order:
    1. Environment variable (GORILLA_API_KEY or API_KEY)
    2. Config file (.env or config.json)
    3. API key service/fetch (if implemented)
    4. Default API key
    
    Args:
        source: Optional specific source to fetch from ('env', 'file', 'api', 'default')
        
    Returns:
        API key string or None if not found
    """
    # Priority 1: Environment variables
    if source is None or source == 'env':
        api_key = os.environ.get('GORILLA_API_KEY') or os.environ.get('API_KEY')
        if api_key:
            logger.info("API key loaded from environment variable")
            return api_key
    
    # Priority 2: Config file (.env)
    if source is None or source == 'file':
        try:
            # Try loading from .env file
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('GORILLA_API_KEY=') or line.startswith('API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"\'')
                            if api_key:
                                logger.info("API key loaded from .env file")
                                return api_key
        except Exception as e:
            logger.debug(f"Could not read .env file: {e}")
        
        # Try loading from config.json
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    api_key = config.get('gorilla_api_key') or config.get('api_key')
                    if api_key:
                        logger.info("API key loaded from config.json")
                        return api_key
        except Exception as e:
            logger.debug(f"Could not read config.json: {e}")
    
    # Priority 3: Fetch from API key service (if implemented)
    if source is None or source == 'api':
        # Try fetching from a remote API key service
        try:
            key_service_url = os.environ.get('API_KEY_SERVICE_URL', '')
            if key_service_url:
                response = requests.get(
                    key_service_url,
                    timeout=5,
                    headers={'Content-Type': 'application/json'}
                )
                if response.status_code == 200:
                    data = response.json()
                    api_key = data.get('api_key') or data.get('key')
                    if api_key:
                        logger.info("API key fetched from remote service")
                        return api_key
        except Exception as e:
            logger.debug(f"Could not fetch API key from remote service: {e}")
    
    # Priority 4: Default key
    if source == 'default' or source is None:
        logger.info("Using default API key")
        return DEFAULT_API_KEY
    
    return None


def update_api_key(new_key: str, save_to_env: bool = False) -> bool:
    """
    Update the API key and optionally save it
    
    Args:
        new_key: New API key to use
        save_to_env: Whether to save to .env file
        
    Returns:
        True if successful
    """
    global DEFAULT_API_KEY
    DEFAULT_API_KEY = new_key
    
    if save_to_env:
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            # Read existing .env or create new
            env_vars = {}
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
            
            # Update or add API key
            env_vars['GORILLA_API_KEY'] = new_key
            
            # Write back
            with open(env_path, 'w') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            logger.info(f"API key saved to {env_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save API key to .env: {e}")
            return False
    
    return True


@dataclass
class HealthcareFacility:
    """Represents a healthcare facility on the map"""
    id: str
    name: str
    facility_type: str
    address: str
    latitude: float
    longitude: float
    services: List[str]
    rating: Optional[float] = None
    phone: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class DatabaseManager:
    """Manages SQL database operations for healthcare facilities"""
    
    def __init__(self, db_path: str = "healthcare_map.db"):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Main facilities table with core attributes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facilities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    facility_type TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    rating REAL,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Services table (many-to-many relationship)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facility_services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facility_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    FOREIGN KEY (facility_id) REFERENCES facilities(id) ON DELETE CASCADE,
                    UNIQUE(facility_id, service_name)
                )
            """)
            
            # Flexible attributes table for extensible attributes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facility_attributes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facility_id TEXT NOT NULL,
                    attribute_key TEXT NOT NULL,
                    attribute_value TEXT,
                    attribute_type TEXT DEFAULT 'text',
                    FOREIGN KEY (facility_id) REFERENCES facilities(id) ON DELETE CASCADE,
                    UNIQUE(facility_id, attribute_key)
                )
            """)
            
            # Indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_facility_type ON facilities(facility_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_facility_services ON facility_services(facility_id, service_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_facility_attributes ON facility_attributes(facility_id, attribute_key)
            """)
            
            logger.info("Database initialized successfully")
    
    def add_facility(
        self,
        facility_id: str,
        name: str,
        facility_type: str,
        address: str,
        latitude: float,
        longitude: float,
        services: List[str],
        rating: Optional[float] = None,
        phone: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a new healthcare facility to the database
        
        Args:
            facility_id: Unique identifier for the facility
            name: Facility name
            facility_type: Type of facility (hospital, clinic, etc.)
            address: Physical address
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            services: List of services offered
            rating: Optional rating (0-5)
            phone: Optional phone number
            attributes: Optional dictionary of additional attributes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert main facility record
                cursor.execute("""
                    INSERT OR REPLACE INTO facilities 
                    (id, name, facility_type, address, latitude, longitude, rating, phone, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (facility_id, name, facility_type, address, latitude, longitude, rating, phone))
                
                # Delete existing services
                cursor.execute("DELETE FROM facility_services WHERE facility_id = ?", (facility_id,))
                
                # Insert services
                for service in services:
                    cursor.execute("""
                        INSERT INTO facility_services (facility_id, service_name)
                        VALUES (?, ?)
                    """, (facility_id, service))
                
                # Delete existing attributes
                cursor.execute("DELETE FROM facility_attributes WHERE facility_id = ?", (facility_id,))
                
                # Insert attributes
                if attributes:
                    for key, value in attributes.items():
                        attr_type = self._determine_attribute_type(value)
                        value_str = json.dumps(value) if not isinstance(value, str) else value
                        cursor.execute("""
                            INSERT INTO facility_attributes 
                            (facility_id, attribute_key, attribute_value, attribute_type)
                            VALUES (?, ?, ?, ?)
                        """, (facility_id, key, value_str, attr_type))
                
                logger.info(f"Facility {facility_id} added successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error adding facility {facility_id}: {e}")
            return False
    
    def _determine_attribute_type(self, value: Any) -> str:
        """Determine the type of an attribute value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, dict) or isinstance(value, list):
            return "json"
        else:
            return "text"
    
    def get_facility(self, facility_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a facility by ID with all attributes
        
        Args:
            facility_id: Facility identifier
            
        Returns:
            Dictionary with facility data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get main facility data
                cursor.execute("SELECT * FROM facilities WHERE id = ?", (facility_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                facility = dict(row)
                
                # Get services
                cursor.execute("""
                    SELECT service_name FROM facility_services 
                    WHERE facility_id = ? ORDER BY service_name
                """, (facility_id,))
                facility['services'] = [row[0] for row in cursor.fetchall()]
                
                # Get attributes
                cursor.execute("""
                    SELECT attribute_key, attribute_value, attribute_type 
                    FROM facility_attributes WHERE facility_id = ?
                """, (facility_id,))
                
                attributes = {}
                for attr_row in cursor.fetchall():
                    key, value_str, attr_type = attr_row
                    attributes[key] = self._parse_attribute_value(value_str, attr_type)
                
                facility['attributes'] = attributes
                
                return facility
                
        except Exception as e:
            logger.error(f"Error retrieving facility {facility_id}: {e}")
            return None
    
    def _parse_attribute_value(self, value_str: str, attr_type: str) -> Any:
        """Parse attribute value based on its type"""
        if attr_type == "json":
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
        elif attr_type == "boolean":
            return value_str.lower() == "true"
        elif attr_type == "integer":
            return int(value_str)
        elif attr_type == "float":
            return float(value_str)
        else:
            return value_str
    
    def search_facilities(
        self,
        facility_type: Optional[str] = None,
        service: Optional[str] = None,
        min_rating: Optional[float] = None,
        attribute_filters: Optional[Dict[str, Any]] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        max_distance_miles: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for facilities matching criteria
        
        Args:
            facility_type: Filter by facility type
            service: Filter by service name
            min_rating: Minimum rating filter
            attribute_filters: Dictionary of attribute key-value pairs to filter by
            
        Returns:
            List of facility dictionaries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                query = """
                    SELECT DISTINCT f.* FROM facilities f
                """
                conditions = []
                params = []
                
                if facility_type:
                    conditions.append("f.facility_type = ?")
                    params.append(facility_type)
                
                if service:
                    query += """
                        INNER JOIN facility_services fs ON f.id = fs.facility_id
                    """
                    conditions.append("fs.service_name LIKE ?")
                    params.append(f"%{service}%")
                
                if min_rating is not None:
                    conditions.append("f.rating >= ?")
                    params.append(min_rating)
                
                # Handle attribute filters
                if attribute_filters:
                    for idx, (attr_key, attr_value) in enumerate(attribute_filters.items()):
                        query += f"""
                            INNER JOIN facility_attributes fa{idx} ON f.id = fa{idx}.facility_id
                        """
                        conditions.append(f"fa{idx}.attribute_key = ?")
                        params.append(attr_key)
                        conditions.append(f"fa{idx}.attribute_value LIKE ?")
                        params.append(f"%{str(attr_value)}%")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                cursor.execute(query, params)
                
                facilities = []
                for row in cursor.fetchall():
                    facility_id = row['id']
                    facility = self.get_facility(facility_id)
                    if facility:
                        # Calculate distance if coordinates provided
                        if latitude and longitude:
                            distance = self._calculate_distance(
                                latitude, longitude,
                                facility['latitude'], facility['longitude']
                            )
                            facility['distance_miles'] = distance
                            
                            if max_distance_miles and distance > max_distance_miles:
                                continue
                        
                        facilities.append(facility)
                
                # Sort by distance if available
                if latitude and longitude:
                    facilities.sort(key=lambda x: x.get('distance_miles', float('inf')))
                
                return facilities
                
        except Exception as e:
            logger.error(f"Error searching facilities: {e}")
            return []
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in miles using Haversine formula"""
        R = 3959  # Earth radius in miles
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    def update_facility_attribute(
        self,
        facility_id: str,
        attribute_key: str,
        attribute_value: Any
    ) -> bool:
        """
        Update or add a specific attribute for a facility
        
        Args:
            facility_id: Facility identifier
            attribute_key: Attribute key name
            attribute_value: Attribute value
            
        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                attr_type = self._determine_attribute_type(attribute_value)
                value_str = json.dumps(attribute_value) if not isinstance(attribute_value, str) else attribute_value
                
                cursor.execute("""
                    INSERT OR REPLACE INTO facility_attributes 
                    (facility_id, attribute_key, attribute_value, attribute_type)
                    VALUES (?, ?, ?, ?)
                """, (facility_id, attribute_key, value_str, attr_type))
                
                # Update facility updated_at timestamp
                cursor.execute("""
                    UPDATE facilities SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (facility_id,))
                
                logger.info(f"Updated attribute {attribute_key} for facility {facility_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating attribute: {e}")
            return False
    
    def delete_facility(self, facility_id: str) -> bool:
        """Delete a facility and all related data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM facilities WHERE id = ?", (facility_id,))
                logger.info(f"Facility {facility_id} deleted")
                return True
        except Exception as e:
            logger.error(f"Error deleting facility: {e}")
            return False
    
    def get_all_facility_ids(self) -> List[str]:
        """Get list of all facility IDs"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM facilities")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting facility IDs: {e}")
            return []


class GorillaLLMClient:
    """Client for interacting with Gorilla LLM API"""
    
    def __init__(self, api_url: str = "https://api.gorilla.cs.berkeley.edu/openfunctions/v2", 
                 api_key: Optional[str] = None, fetch_key_on_init: bool = True):
        """
        Initialize the Gorilla LLM client
        
        Args:
            api_url: The Gorilla API endpoint URL
            api_key: API key for authentication (if None, will fetch from available sources)
            fetch_key_on_init: Whether to automatically fetch API key if not provided
        """
        self.api_url = api_url
        self.session = requests.Session()
        
        # Fetch API key if not provided
        if api_key is None and fetch_key_on_init:
            self.api_key = get_api_key()
        else:
            self.api_key = api_key or DEFAULT_API_KEY
        
        # Set up session headers with API key if available
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Key": self.api_key
            })
    
    def refresh_api_key(self, source: Optional[str] = None) -> bool:
        """
        Refresh the API key from available sources
        
        Args:
            source: Optional specific source to fetch from ('env', 'file', 'api', 'default')
            
        Returns:
            True if API key was successfully refreshed
        """
        new_key = get_api_key(source=source)
        if new_key:
            self.api_key = new_key
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Key": self.api_key
            })
            logger.info("API key refreshed successfully")
            return True
        return False
    
    def set_api_key(self, new_key: str, save_to_env: bool = False) -> bool:
        """
        Set a new API key for this client instance
        
        Args:
            new_key: New API key to use
            save_to_env: Whether to save to .env file
            
        Returns:
            True if successful
        """
        if update_api_key(new_key, save_to_env=save_to_env):
            self.api_key = new_key
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Key": self.api_key
            })
            return True
        return False
        
    def get_healthcare_functions(self) -> List[Dict]:
        """Define available healthcare-related functions for Gorilla"""
        return [
            {
                "name": "find_healthcare_facilities",
                "description": "Find healthcare facilities near a location or matching specific criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location name, address, or coordinates (lat,lon)"
                        },
                        "facility_type": {
                            "type": "string",
                            "description": "Type of facility (hospital, clinic, pharmacy, urgent_care, etc.)",
                            "enum": ["hospital", "clinic", "pharmacy", "urgent_care", "specialist", "emergency_room"]
                        },
                        "service": {
                            "type": "string",
                            "description": "Specific service needed (e.g., cardiology, pediatrics, mental_health)"
                        },
                        "radius": {
                            "type": "number",
                            "description": "Search radius in miles (default: 10)"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "get_facility_details",
                "description": "Get detailed information about a specific healthcare facility",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "facility_id": {
                            "type": "string",
                            "description": "Unique identifier of the facility"
                        }
                    },
                    "required": ["facility_id"]
                }
            },
            {
                "name": "search_facilities_by_service",
                "description": "Search for facilities offering a specific healthcare service",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service name (e.g., MRI, vaccination, dental, therapy)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location to search around"
                        },
                        "radius": {
                            "type": "number",
                            "description": "Search radius in miles"
                        }
                    },
                    "required": ["service", "location"]
                }
            },
            {
                "name": "get_patient_health_data",
                "description": "Retrieve patient health records and information (requires authentication)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Unique patient identifier"
                        },
                        "data_type": {
                            "type": "string",
                            "description": "Type of data to retrieve",
                            "enum": ["all", "appointments", "prescriptions", "lab_results", "conditions"]
                        }
                    },
                    "required": ["patient_id"]
                }
            },
            {
                "name": "schedule_appointment",
                "description": "Schedule a healthcare appointment at a facility",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "facility_id": {
                            "type": "string",
                            "description": "ID of the healthcare facility"
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Type of service or appointment"
                        },
                        "date": {
                            "type": "string",
                            "description": "Preferred date in YYYY-MM-DD format"
                        },
                        "patient_id": {
                            "type": "string",
                            "description": "Patient identifier"
                        }
                    },
                    "required": ["facility_id", "service_type", "date"]
                }
            }
        ]
    
    def generate_function_call(self, user_prompt: str, custom_functions: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        Send a natural language prompt to Gorilla LLM and get function call suggestion
        
        Args:
            user_prompt: Natural language instruction from user
            custom_functions: Optional custom functions list, defaults to healthcare functions
            
        Returns:
            Dictionary containing function name and arguments, or None if error
        """
        if custom_functions is None:
            custom_functions = self.get_healthcare_functions()
        
        payload = {
            "prompt": user_prompt,
            "functions": custom_functions
        }
        
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                headers["X-API-Key"] = self.api_key
            
            response = self.session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("function_call") or result
            elif response.status_code == 401:
                # Unauthorized - API key might be invalid, try refreshing
                logger.warning("API key authentication failed. Attempting to refresh...")
                if self.refresh_api_key():
                    # Retry the request with new key
                    headers = {"Content-Type": "application/json"}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                        headers["X-API-Key"] = self.api_key
                    retry_response = self.session.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    if retry_response.status_code == 200:
                        result = retry_response.json()
                        return result.get("function_call") or result
                
                logger.error(f"Authentication failed after refresh: HTTP {response.status_code}")
                print(f"Error: HTTP {response.status_code} - Authentication failed")
                print(f"Response: {response.text}")
                return None
            else:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None


class HealthcareMapAI:
    """AI-powered healthcare map application"""
    
    def __init__(
        self,
        gorilla_client: Optional[GorillaLLMClient] = None,
        db_path: str = "healthcare_map.db",
        initialize_sample_data: bool = True
    ):
        """
        Initialize the healthcare map AI system
        
        Args:
            gorilla_client: Optional Gorilla LLM client instance
            db_path: Path to SQLite database file
            initialize_sample_data: Whether to populate with sample data if database is empty
        """
        self.gorilla_client = gorilla_client or GorillaLLMClient()
        self.db_manager = DatabaseManager(db_path)
        
        # Initialize sample data if database is empty
        if initialize_sample_data:
            self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize database with sample healthcare facilities if empty"""
        existing_ids = self.db_manager.get_all_facility_ids()
        if existing_ids:
            logger.info(f"Database already contains {len(existing_ids)} facilities. Skipping sample data initialization.")
            return
        
        logger.info("Initializing database with sample data...")
        sample_facilities = [
            {
                "id": "hosp_001",
                "name": "City General Hospital",
                "facility_type": "hospital",
                "address": "123 Main St, City, State 12345",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "services": ["emergency", "surgery", "cardiology", "pediatrics", "mri", "xray"],
                "rating": 4.5,
                "phone": "(555) 123-4567",
                "attributes": {
                    "bed_count": 250,
                    "emergency_room": True,
                    "accepts_insurance": ["Medicare", "Medicaid", "Blue Cross"],
                    "parking_available": True,
                    "visiting_hours": "24/7"
                }
            },
            {
                "id": "clinic_001",
                "name": "Downtown Health Clinic",
                "facility_type": "clinic",
                "address": "456 Oak Ave, City, State 12345",
                "latitude": 40.7589,
                "longitude": -73.9851,
                "services": ["primary_care", "vaccination", "lab_tests", "mental_health"],
                "rating": 4.2,
                "phone": "(555) 234-5678",
                "attributes": {
                    "accepts_walk_ins": True,
                    "languages_spoken": ["English", "Spanish", "French"],
                    "wheelchair_accessible": True,
                    "parking_available": False
                }
            },
            {
                "id": "pharm_001",
                "name": "Central Pharmacy",
                "facility_type": "pharmacy",
                "address": "789 Elm St, City, State 12345",
                "latitude": 40.7489,
                "longitude": -73.9680,
                "services": ["prescription", "vaccination", "flu_shot"],
                "rating": 4.0,
                "phone": "(555) 345-6789",
                "attributes": {
                    "drive_through": True,
                    "open_24_hours": False,
                    "delivery_available": True
                }
            },
            {
                "id": "urgent_001",
                "name": "Express Urgent Care",
                "facility_type": "urgent_care",
                "address": "321 Pine Rd, City, State 12345",
                "latitude": 40.7280,
                "longitude": -73.9942,
                "services": ["urgent_care", "xray", "lab_tests", "sutures"],
                "rating": 4.3,
                "phone": "(555) 456-7890",
                "attributes": {
                    "average_wait_time_minutes": 25,
                    "accepts_walk_ins": True,
                    "xray_on_site": True
                }
            }
        ]
        
        for facility_data in sample_facilities:
            attributes = facility_data.pop("attributes", None)
            self.db_manager.add_facility(
                attributes=attributes,
                **facility_data
            )
        
        logger.info("Sample data initialization complete.")
    
    def process_natural_language_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a natural language query using Gorilla LLM
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            Dictionary with results and metadata
        """
        print(f"\n🔍 Processing query: '{user_query}'")
        
        # Get function call from Gorilla LLM
        function_call = self.gorilla_client.generate_function_call(user_query)
        
        if not function_call:
            return {
                "success": False,
                "error": "Failed to generate function call from Gorilla LLM",
                "query": user_query
            }
        
        function_name = function_call.get("name") or function_call.get("function")
        arguments = function_call.get("arguments") or function_call.get("args", {})
        
        # Parse arguments if they're a string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        
        print(f"✅ Generated function call: {function_name}")
        print(f"📋 Arguments: {arguments}")
        
        # Execute the function
        result = self._execute_function(function_name, arguments)
        
        return {
            "success": True,
            "function_name": function_name,
            "arguments": arguments,
            "result": result,
            "query": user_query,
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute the function call generated by Gorilla LLM
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments
            
        Returns:
            Function execution result
        """
        if function_name == "find_healthcare_facilities":
            return self.find_healthcare_facilities(**arguments)
        elif function_name == "get_facility_details":
            return self.get_facility_details(**arguments)
        elif function_name == "search_facilities_by_service":
            return self.search_facilities_by_service(**arguments)
        elif function_name == "get_patient_health_data":
            return self.get_patient_health_data(**arguments)
        elif function_name == "schedule_appointment":
            return self.schedule_appointment(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def find_healthcare_facilities(
        self,
        location: str,
        facility_type: Optional[str] = None,
        service: Optional[str] = None,
        radius: float = 10.0
    ) -> Dict[str, Any]:
        """Find healthcare facilities matching criteria"""
        # Search database for matching facilities
        facilities = self.db_manager.search_facilities(
            facility_type=facility_type,
            service=service
        )
        
        # Format results
        results = []
        for facility in facilities:
            results.append({
                "id": facility["id"],
                "name": facility["name"],
                "type": facility["facility_type"],
                "address": facility["address"],
                "coordinates": {"lat": facility["latitude"], "lon": facility["longitude"]},
                "services": facility.get("services", []),
                "rating": facility.get("rating"),
                "phone": facility.get("phone"),
                "attributes": facility.get("attributes", {})
            })
        
        return {
            "location": location,
            "radius_miles": radius,
            "facilities_found": len(results),
            "facilities": results
        }
    
    def get_facility_details(self, facility_id: str) -> Dict[str, Any]:
        """Get detailed information about a facility"""
        facility = self.db_manager.get_facility(facility_id)
        
        if not facility:
            return {"error": f"Facility {facility_id} not found"}
        
        return {
            "id": facility["id"],
            "name": facility["name"],
            "type": facility["facility_type"],
            "address": facility["address"],
            "coordinates": {"lat": facility["latitude"], "lon": facility["longitude"]},
            "services": facility.get("services", []),
            "rating": facility.get("rating"),
            "phone": facility.get("phone"),
            "attributes": facility.get("attributes", {}),
            "created_at": facility.get("created_at"),
            "updated_at": facility.get("updated_at"),
            "full_details": True
        }
    
    def search_facilities_by_service(
        self,
        service: str,
        location: str,
        radius: float = 10.0
    ) -> Dict[str, Any]:
        """Search for facilities offering a specific service"""
        return self.find_healthcare_facilities(
            location=location,
            service=service,
            radius=radius
        )
    
    def get_patient_health_data(
        self,
        patient_id: str,
        data_type: str = "all"
    ) -> Dict[str, Any]:
        """Retrieve patient health data (simulated)"""
        # In a real application, this would query a secure database
        return {
            "patient_id": patient_id,
            "data_type": data_type,
            "message": "Patient data retrieval requires authentication",
            "note": "This is a simulated response. In production, implement secure patient data access."
        }
    
    def schedule_appointment(
        self,
        facility_id: str,
        service_type: str,
        date: str,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedule an appointment"""
        facility = self.db_manager.get_facility(facility_id)
        
        if not facility:
            return {"error": f"Facility {facility_id} not found"}
        
        # Store appointment in attributes (in a real system, you'd have a separate appointments table)
        appointment_id = f"apt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        appointments = facility.get("attributes", {}).get("appointments", [])
        appointments.append({
            "appointment_id": appointment_id,
            "service_type": service_type,
            "date": date,
            "patient_id": patient_id,
            "status": "scheduled"
        })
        
        self.db_manager.update_facility_attribute(
            facility_id,
            "appointments",
            appointments
        )
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "facility": facility["name"],
            "facility_id": facility_id,
            "service": service_type,
            "date": date,
            "patient_id": patient_id,
            "status": "scheduled",
            "message": "Appointment scheduled successfully"
        }
    
    def add_facility(
        self,
        facility_id: str,
        name: str,
        facility_type: str,
        address: str,
        latitude: float,
        longitude: float,
        services: List[str],
        rating: Optional[float] = None,
        phone: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a new healthcare facility to the database
        
        Args:
            facility_id: Unique identifier for the facility
            name: Facility name
            facility_type: Type of facility (hospital, clinic, etc.)
            address: Physical address
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            services: List of services offered
            rating: Optional rating (0-5)
            phone: Optional phone number
            attributes: Optional dictionary of additional attributes
            
        Returns:
            True if successful, False otherwise
        """
        return self.db_manager.add_facility(
            facility_id=facility_id,
            name=name,
            facility_type=facility_type,
            address=address,
            latitude=latitude,
            longitude=longitude,
            services=services,
            rating=rating,
            phone=phone,
            attributes=attributes
        )
    
    def update_facility_attribute(
        self,
        facility_id: str,
        attribute_key: str,
        attribute_value: Any
    ) -> bool:
        """
        Update or add a custom attribute for a facility
        
        Args:
            facility_id: Facility identifier
            attribute_key: Attribute key name
            attribute_value: Attribute value (can be any type)
            
        Returns:
            True if successful
        """
        return self.db_manager.update_facility_attribute(
            facility_id,
            attribute_key,
            attribute_value
        )
    
    def search_by_attribute(
        self,
        attribute_key: str,
        attribute_value: Any,
        facility_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for facilities by custom attribute
        
        Args:
            attribute_key: The attribute key to search for
            attribute_value: The value to match (partial matching supported)
            facility_type: Optional facility type filter
            
        Returns:
            List of matching facilities
        """
        attribute_filters = {attribute_key: attribute_value}
        return self.db_manager.search_facilities(
            facility_type=facility_type,
            attribute_filters=attribute_filters
        )
    
    def process_frontend_query(
        self,
        user_input: str,
        severity: str = "critical",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Process user query for frontend - returns format compatible with healthnav.js
        
        Args:
            user_input: User's message describing condition
            severity: Patient severity level (critical/stable)
            latitude: Optional incident latitude
            longitude: Optional incident longitude
            
        Returns:
            Dictionary with 'message' and 'recommendations' keys
        """
        # Try to get structured query from Gorilla LLM
        function_call = self.gorilla_client.generate_function_call(user_input)
        
        # Extract search criteria
        service = None
        facility_type = "hospital"
        condition = None
        
        if function_call:
            args = function_call.get("arguments") or function_call.get("args", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    args = {}
            
            service = args.get("service") or args.get("condition")
            condition = args.get("condition")
            if args.get("facility_type"):
                facility_type = args.get("facility_type")
        
        # Fallback to keyword matching
        user_lower = user_input.lower()
        if not service:
            if any(word in user_lower for word in ["cardiac", "heart", "heart attack"]):
                service = "Cardiology"
                condition = "cardiac"
            elif "stroke" in user_lower:
                service = "Stroke Center"
                condition = "stroke"
            elif "trauma" in user_lower:
                service = "Trauma"
                condition = "trauma"
        
        # Generate AI message
        message = self._generate_frontend_message(condition or user_input, severity)
        
        # Search for facilities
        facilities = self.db_manager.search_facilities(
            facility_type=facility_type,
            service=service,
            latitude=latitude,
            longitude=longitude,
            max_distance_miles=20 if severity == "critical" else 30
        )
        
        # Format recommendations for frontend
        recommendations = []
        for facility in facilities[:5]:  # Limit to 5
            distance = facility.get('distance_miles', 0)
            eta = self._calculate_eta(distance, severity)
            
            # Get tags from services
            tags = facility.get('services', [])[:4]  # Limit tags
            
            recommendations.append({
                "name": facility["name"],
                "eta": eta,
                "tags": tags,
                "id": facility.get("id"),
                "lat": facility.get("latitude"),
                "lng": facility.get("longitude"),
                "distance": round(distance, 1) if distance else None,
                "rating": facility.get("rating"),
                "phone": facility.get("phone")
            })
        
        return {
            "message": message,
            "recommendations": recommendations
        }
    
    def _generate_frontend_message(self, condition: str, severity: str) -> str:
        """Generate AI response message for frontend"""
        condition_lower = condition.lower()
        
        if "cardiac" in condition_lower or "heart" in condition_lower:
            return f"Detected possible cardiac emergency ({severity.upper()} priority). Recommending cardiac-capable hospitals with ICU and 24/7 emergency services."
        elif "stroke" in condition_lower:
            return f"Suspected stroke ({severity.upper()} priority). Prioritizing stroke-certified facilities with neurology departments and CT scan availability."
        elif "trauma" in condition_lower:
            return f"Trauma incident detected ({severity.upper()} priority). Showing nearest Level I trauma centers with helicopter access and trauma teams."
        else:
            return f"Medical condition noted ({severity.upper()} priority). Displaying nearby hospitals and emergency facilities."
    
    def _calculate_eta(self, distance_miles: float, severity: str) -> str:
        """Calculate estimated time of arrival"""
        if distance_miles <= 0:
            return "Unknown"
        
        # Assume average speed: 40 mph for critical, 30 mph for stable
        avg_speed = 40 if severity == "critical" else 30
        minutes = int((distance_miles / avg_speed) * 60)
        
        if minutes < 1:
            return "<1 min"
        elif minutes < 60:
            return f"{minutes} min"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    
    def get_all_facilities_for_map(self) -> List[Dict[str, Any]]:
        """Get all facilities formatted for map display"""
        facilities = self.db_manager.get_all_facility_ids()
        map_facilities = []
        for fid in facilities:
            facility = self.db_manager.get_facility(fid)
            if facility:
                map_facilities.append({
                    "id": facility["id"],
                    "name": facility["name"],
                    "lat": facility["latitude"],
                    "lng": facility["longitude"],
                    "tags": facility.get("services", [])[:3],
                    "type": facility["facility_type"],
                    "rating": facility.get("rating"),
                    "phone": facility.get("phone")
                })
        return map_facilities


def main():
    """Main function to demonstrate the AI Healthcare Map"""
    print("🏥 AI Healthcare Map with Gorilla LLM Integration")
    print("=" * 60)
    
    # Initialize the healthcare map AI
    healthcare_map = HealthcareMapAI()
    
    # Example queries to demonstrate functionality
    example_queries = [
        "Find hospitals near downtown",
        "Search for pharmacies that offer vaccination services",
        "I need to find a clinic with mental health services",
        "Get details about facility hosp_001",
        "Find urgent care facilities",
        "Schedule an appointment at clinic_001 for primary care on 2024-12-15"
    ]
    
    print("\n📝 Running example queries...")
    print("-" * 60)
    
    for query in example_queries:
        result = healthcare_map.process_natural_language_query(query)
        
        if result["success"]:
            print(f"\n📊 Results:")
            print(json.dumps(result["result"], indent=2))
        else:
            print(f"\n❌ Error: {result.get('error')}")
        
        print("\n" + "-" * 60)
    
    # Interactive mode
    print("\n💬 Interactive Mode - Enter your queries (type 'exit' to quit)")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n🔍 Your query: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            result = healthcare_map.process_natural_language_query(user_input)
            
            if result["success"]:
                print(f"\n📊 Results:")
                print(json.dumps(result["result"], indent=2))
            else:
                print(f"\n❌ Error: {result.get('error')}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


# ====== FLASK SERVER MODE ======
# Initialize Flask app if available
if FLASK_AVAILABLE:
    # Path to frontend files (adjust if needed)
    FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tamucc-ai-hackathon")
    if not os.path.exists(FRONTEND_DIR):
        # Try alternative path
        FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "tamucc-ai-hackathon")
    
    app = Flask(__name__, static_folder=FRONTEND_DIR if os.path.exists(FRONTEND_DIR) else None, static_url_path='')
    CORS(app)
    
    # Global healthcare map instance
    _healthcare_map = None
    
    def get_healthcare_map():
        """Get or create healthcare map instance"""
        global _healthcare_map
        if _healthcare_map is None:
            _healthcare_map = HealthcareMapAI()
        return _healthcare_map
    
    @app.route('/')
    def index():
        """Serve the main HTML file"""
        if os.path.exists(FRONTEND_DIR):
            return send_from_directory(FRONTEND_DIR, 'frontendhealthnav.html')
        return jsonify({"error": "Frontend files not found"}), 404
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve static files (CSS, JS)"""
        if os.path.exists(FRONTEND_DIR):
            return send_from_directory(FRONTEND_DIR, filename)
        return jsonify({"error": "File not found"}), 404
    
    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Handle chat requests from frontend"""
        try:
            data = request.get_json()
            user_input = data.get('message', '').strip()
            severity = data.get('severity', 'critical')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not user_input:
                return jsonify({"error": "Message is required"}), 400
            
            healthcare_map = get_healthcare_map()
            result = healthcare_map.process_frontend_query(
                user_input=user_input,
                severity=severity,
                latitude=latitude,
                longitude=longitude
            )
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            return jsonify({"error": str(e), "message": "An error occurred processing your request"}), 500
    
    @app.route('/api/facilities', methods=['GET'])
    def get_facilities():
        """Get all facilities for map display"""
        try:
            healthcare_map = get_healthcare_map()
            facilities = healthcare_map.get_all_facilities_for_map()
            return jsonify({"facilities": facilities})
        except Exception as e:
            logger.error(f"Error getting facilities: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/facility/<facility_id>', methods=['GET'])
    def get_facility(facility_id):
        """Get details for a specific facility"""
        try:
            healthcare_map = get_healthcare_map()
            facility = healthcare_map.db_manager.get_facility(facility_id)
            if not facility:
                return jsonify({"error": "Facility not found"}), 404
            return jsonify(facility)
        except Exception as e:
            logger.error(f"Error getting facility: {e}")
            return jsonify({"error": str(e)}), 500
    
    def run_server(port=5000, host='0.0.0.0', debug=True):
        """Run the Flask server"""
        logger.info(f"Starting Flask server on {host}:{port}")
        logger.info(f"Frontend directory: {FRONTEND_DIR}")
        logger.info(f"Access the app at: http://localhost:{port}")
        app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import sys
    
    # Check if server mode requested
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        if not FLASK_AVAILABLE:
            print("❌ Flask not available. Install with: pip install flask flask-cors")
            sys.exit(1)
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        run_server(port=port)
    else:
        # Run in CLI mode
        main()

