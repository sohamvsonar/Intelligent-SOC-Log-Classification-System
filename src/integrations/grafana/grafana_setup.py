#!/usr/bin/env python3
"""
Grafana Setup and Configuration Script for SOC System
Automatically configures Grafana data source and imports the SOC dashboard
"""

import os
import json
import requests
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GrafanaSetup:
    def __init__(self):
        self.grafana_url = os.getenv('GRAFANA_URL', 'http://localhost:3000')
        self.grafana_user = os.getenv('GRAFANA_USER', 'admin')
        self.grafana_password = os.getenv('GRAFANA_PASSWORD', 'admin')
        self.api_url = os.getenv('SOC_API_URL', 'http://localhost:8002')
        
        self.session = requests.Session()
        self.session.auth = (self.grafana_user, self.grafana_password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def wait_for_grafana(self, timeout: int = 60) -> bool:
        """Wait for Grafana to be available"""
        print("Waiting for Grafana to be available...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.grafana_url}/api/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Grafana is available!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print("⏳ Waiting for Grafana...")
            time.sleep(5)
        
        print("❌ Grafana is not available after timeout")
        return False
    
    def test_api_connection(self) -> bool:
        """Test connection to our SOC API"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            if response.status_code == 200:
                print("✅ SOC API is available!")
                return True
            else:
                print(f"⚠️ SOC API returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ SOC API connection failed: {e}")
            return False
    
    def create_data_source(self) -> bool:
        """Create JSON data source for SOC API"""
        print("Setting up Grafana data source...")
        
        datasource_config = {
            "name": "SOC_API",
            "type": "grafana-simple-json-datasource",
            "url": self.api_url,
            "access": "proxy",
            "isDefault": True,
            "jsonData": {
                "httpMethod": "POST",
                "keepCookies": []
            }
        }
        
        try:
            # Check if data source already exists
            response = self.session.get(f"{self.grafana_url}/api/datasources/name/SOC_API")
            if response.status_code == 200:
                print("✅ SOC_API data source already exists")
                return True
            
            # Create new data source
            response = self.session.post(
                f"{self.grafana_url}/api/datasources",
                json=datasource_config
            )
            
            if response.status_code == 200:
                print("✅ SOC_API data source created successfully!")
                return True
            else:
                print(f"❌ Failed to create data source: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating data source: {e}")
            return False
    
    def import_dashboard(self) -> bool:
        """Import SOC dashboard configuration"""
        print("Importing SOC dashboard...")
        
        try:
            # Load dashboard JSON
            dashboard_path = os.path.join(os.path.dirname(__file__), 'soc_dashboard.json')
            with open(dashboard_path, 'r') as f:
                dashboard_config = json.load(f)
            
            # Prepare import payload
            import_payload = {
                "dashboard": dashboard_config["dashboard"],
                "overwrite": True,
                "inputs": [
                    {
                        "name": "DS_SOC_API",
                        "type": "datasource",
                        "pluginId": "grafana-simple-json-datasource",
                        "value": "SOC_API"
                    }
                ]
            }
            
            response = self.session.post(
                f"{self.grafana_url}/api/dashboards/import",
                json=import_payload
            )
            
            if response.status_code == 200:
                result = response.json()
                dashboard_url = f"{self.grafana_url}/d/{result['uid']}"
                print(f"✅ SOC dashboard imported successfully!")
                print(f"   Dashboard URL: {dashboard_url}")
                return True
            else:
                print(f"❌ Failed to import dashboard: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error importing dashboard: {e}")
            return False
    
    def create_folder(self, folder_name: str = "SOC") -> bool:
        """Create folder for SOC dashboards"""
        try:
            folder_config = {
                "title": folder_name
            }
            
            response = self.session.post(
                f"{self.grafana_url}/api/folders",
                json=folder_config
            )
            
            if response.status_code in [200, 412]:  # 412 means folder already exists
                print(f"✅ Folder '{folder_name}' ready")
                return True
            else:
                print(f"⚠️ Could not create folder: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating folder: {e}")
            return False
    
    def setup_grafana(self) -> bool:
        """Complete Grafana setup process"""
        print("🚀 Starting Grafana setup for SOC system...")
        
        # Wait for Grafana to be available
        if not self.wait_for_grafana():
            return False
        
        # Test SOC API connection
        if not self.test_api_connection():
            print("⚠️ SOC API is not available. Please start the API server first:")
            print("   cd src/integrations/grafana && python grafana_api.py")
            return False
        
        # Create folder
        self.create_folder()
        
        # Create data source
        if not self.create_data_source():
            return False
        
        # Import dashboard
        if not self.import_dashboard():
            return False
        
        print("\n🎉 Grafana setup completed successfully!")
        print(f"   Grafana URL: {self.grafana_url}")
        print(f"   Username: {self.grafana_user}")
        print(f"   Password: {self.grafana_password}")
        print("\nNext steps:")
        print("1. Open Grafana in your browser")
        print("2. Navigate to the SOC Dashboard")
        print("3. Configure time range (last 7 days recommended)")
        
        return True

def main():
    setup = GrafanaSetup()
    success = setup.setup_grafana()
    
    if not success:
        print("\n❌ Grafana setup failed. Please check the logs above.")
        print("\nTroubleshooting:")
        print("1. Make sure Grafana is running: docker run -d -p 3000:3000 grafana/grafana")
        print("2. Make sure SOC API is running: python grafana_api.py")
        print("3. Check Grafana credentials in .env file")
        exit(1)
    
    print("\n✅ Setup completed successfully!")

if __name__ == "__main__":
    main()