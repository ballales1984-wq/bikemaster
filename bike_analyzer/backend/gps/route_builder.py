def build_route(gps_data):
    route = []

    for point in gps_data:
        route.append((point["lat"], point["lon"]))

    return route