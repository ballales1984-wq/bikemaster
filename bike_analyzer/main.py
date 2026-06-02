from backend.data.mock_data import mock_gps_data
from backend.gps.route_builder import build_route
from backend.gps.map_renderer import render_map

def main():
    route = build_route(mock_gps_data)
    render_map(route)

if __name__ == "__main__":
    main()