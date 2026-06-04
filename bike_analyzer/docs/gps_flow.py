FLUXO_GPS = """
# Flusso GPS BikeMaster

## 1. Parsing
- GPX: ingestion/gps_parser.py → parse_gpx_file()
- FIT: ingestion/gps_parser.py → parse_fit_file()

## 2. Validazione
- processing/processing.py → validate_coordinate(), validate_gps_point()

## 3. Processing
- Pulizia outlier: remove_outliers()
- Rilevamento pause: detect_pauses()
- Rilevamento accelerazioni: detect_accelerations/decelerations()
- Segmentazione: build_segments()

## 4. Statistiche
- compute_statistics() → RouteStatistics

## 5. Rendering
- maps/map_renderer.py → create_route_map() con Folium

## 6. Persistenza
- db/database.py → save_ride() con GPS points in JSON

## 7. Analisi
- analytics/analytics.py → analyze_ride()
- analytics/performance.py → performance_score, recovery_score, etc.
"""

def get_gps_flow_doc() -> str:
    return FLUXO_GPS