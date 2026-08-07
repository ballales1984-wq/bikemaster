import os
import sys

os.environ["DB_PATH"] = "D:/BikeMaster/rides.db"
sys.path.insert(0, "D:/BikeMaster")

from bike_analyzer.backend.db.database import get_rides_by_athlete
from bike_analyzer.backend.models.models import Ride

target_id = 7
rows = get_rides_by_athlete(target_id)
print("rows:", len(rows))
for i, r in enumerate(rows[:2]):
    print(f"row {i} gps_points type:", type(r.get("gps_points")))
    print(f"row {i} gps_points len:", len(r.get("gps_points") or []))
    ride = Ride(**r)
    print(f"ride {i} gps_points type:", type(ride.gps_points))
    print(f"ride {i} gps_points len:", len(ride.gps_points or []))
    d = ride.to_dict()
    print(f"ride {i} to_dict keys:", list(d.keys()))
    print(f"ride {i} has gps_points in dict:", "gps_points" in d)
