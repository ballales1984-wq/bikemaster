import json
import os
from typing import List, Dict
from app.models.ride import Ride

def load_rides() -> List[Ride]:
    """Load ride data from mock data file or Google Fit API."""
    # For now, load from mock data
    mock_data_path = os.path.join(
        os.path.dirname(__file__), 
        'mock_data.json'
    )
    
    try:
        with open(mock_data_path, 'r') as f:
            data = json.load(f)
        
        rides = []
        for ride_data in data:
            ride = Ride.from_dict(ride_data)
            rides.append(ride)
        
        return rides
    except FileNotFoundError:
        print(f"Mock data file not found: {mock_data_path}")
        return []
    except Exception as e:
        print(f"Error loading ride data: {e}")
        return []

def load_rides_from_google_fit() -> List[Ride]:
    """Placeholder for Google Fit API integration."""
    # TODO: Implement Google Fit API authentication and data retrieval
    print("Google Fit integration not implemented yet.")
    return []