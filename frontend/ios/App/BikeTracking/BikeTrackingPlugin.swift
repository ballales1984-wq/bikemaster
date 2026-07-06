import Foundation
import CoreLocation

@objc(BikeTrackingPlugin)
public class BikeTrackingPlugin: NSObject {
    private var locationManager: CLLocationManager?
    private var isTracking = false
    private var lastLocation: CLLocation?
    private var distanceFilter: CLLocationDistance = 5.0
    private var startTime: Date?
    private var totalDistance: CLLocationDistance = 0
    private var trackPoints: [(lat: Double, lon: Double, timestamp: Date)] = []

    @objc public func startTracking(_ call: CAPPluginCall) {
        guard CLLocationManager.locationServicesEnabled() else {
            call.reject("Location services disabled")
            return
        }

        let accuracy = call.getString("locationAccuracy") ?? "best"
        distanceFilter = call.getDouble("distanceFilter") ?? 5.0

        locationManager = CLLocationManager()
        locationManager?.delegate = self
        locationManager?.desiredAccuracy = accuracy == "best" ? kCLLocationAccuracyBestForNavigation : kCLLocationAccuracyBest
        locationManager?.distanceFilter = distanceFilter
        locationManager?.allowsBackgroundLocationUpdates = true
        locationManager?.pausesLocationUpdatesAutomatically = false

        locationManager?.requestAlwaysAuthorization()
        locationManager?.startUpdatingLocation()
        locationManager?.startUpdatingHeading()

        isTracking = true
        startTime = Date()
        totalDistance = 0
        trackPoints.removeAll()

        call.resolve([
            "success": true,
            "message": "Tracking started"
        ])
    }

    @objc public func stopTracking(_ call: CAPPluginCall) {
        locationManager?.stopUpdatingLocation()
        locationManager?.stopUpdatingHeading()
        isTracking = false

        let gpxString = buildGPX()
        call.resolve([
            "success": true,
            "gpx": gpxString,
            "distance_m": totalDistance,
            "duration_seconds": startTime.map { Date().timeIntervalSince($0) } ?? 0,
            "points": trackPoints.count
        ])
    }

    @objc public func pauseTracking(_ call: CAPPluginCall) {
        locationManager?.stopUpdatingLocation()
        call.resolve(["success": true])
    }

    @objc public func resumeTracking(_ call: CAPPluginCall) {
        locationManager?.startUpdatingLocation()
        call.resolve(["success": true])
    }

    @objc public func checkPermissions(_ call: CAPPluginCall) {
        let status = CLLocationManager.authorizationStatus()
        let granted = status == .authorizedAlways || status == .authorizedWhenInUse
        call.resolve([
            "granted": granted,
            "status": String(describing: status)
        ])
    }

    private func buildGPX() -> String {
        let formatter = ISO8601DateFormatter()
        var xml = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BikeMaster-iOS">
  <trk>
    <name>BikeMaster ride</name>
    <trkseg>
"""
        for point in trackPoints {
            xml += """
      <trkpt lat="\(point.lat)" lon="\(point.lon)">
        <time>\(formatter.string(from: point.timestamp))</time>
      </trkpt>
"""
        }
        xml += """
    </trkseg>
  </trk>
</gpx>
"""
        return xml
    }
}

extension BikeTrackingPlugin: CLLocationManagerDelegate {
    public func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        lastLocation = location

        if let previous = trackPoints.last {
            totalDistance += location.distance(from: CLLocation(latitude: previous.lat, longitude: previous.lon))
        }

        trackPoints.append((lat: location.coordinate.latitude, lon: location.coordinate.longitude, timestamp: location.timestamp))

        NotificationCenter.default.post(
            name: NSNotification.Name("BikeTrackingLocationUpdate"),
            object: nil,
            userInfo: [
                "lat": location.coordinate.latitude,
                "lon": location.coordinate.longitude,
                "speed": location.speed,
                "altitude": location.altitude,
                "distance_m": totalDistance,
            ]
        )
    }

    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        NotificationCenter.default.post(
            name: NSNotification.Name("BikeTrackingError"),
            object: nil,
            userInfo: ["error": error.localizedDescription]
        )
    }

    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = CLLocationManager.authorizationStatus()
        NotificationCenter.default.post(
            name: NSNotification.Name("BikeTrackingPermissionChange"),
            object: nil,
            userInfo: ["status": String(describing: status)]
        )
    }
}
