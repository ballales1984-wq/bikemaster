import Foundation
import CoreLocation
import UIKit
import Capacitor

@objc(BikeTrackingPlugin)
public class BikeTrackingPlugin: CAPPlugin, CLLocationManagerDelegate {
    private var locationManager: CLLocationManager?
    private var isTracking = false
    private var isPaused = false
    private var startTime: Date?
    private var totalDistance: CLLocationDistance = 0
    private var trackPoints: [(lat: Double, lon: Double, altitude: Double, timestamp: Date)] = []
    private var lastLocation: CLLocation?
    private var backgroundTask: UIBackgroundTaskIdentifier = .invalid
    private let stateKey = "tracking_state"
    private let gpxDirName = "tracks"

    private func documentsDirectory() -> URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
    }

    private func tracksDirectory() -> URL {
        let dir = documentsDirectory().appendingPathComponent(gpxDirName)
        if !FileManager.default.fileExists(atPath: dir.path) {
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        }
        return dir
    }

    private func defaultGpxPath() -> String {
        let file = "track_\(Date().timeIntervalSince1970).gpx"
        return tracksDirectory().appendingPathComponent(file).path
    }

    private func saveTrackingState(tracking: Bool, path: String?) {
        let defaults = UserDefaults.standard
        defaults.set(tracking, forKey: "\(stateKey)_is_tracking")
        defaults.set(path ?? "", forKey: "\(stateKey)_output_path")
    }

    private func clearTrackingState() {
        let defaults = UserDefaults.standard
        defaults.removeObject(forKey: "\(stateKey)_is_tracking")
        defaults.removeObject(forKey: "\(stateKey)_output_path")
    }

    @objc public func startTracking(_ call: CAPPluginCall) {
        guard CLLocationManager.locationServicesEnabled() else {
            call.reject("Location services disabled")
            return
        }

        let accuracy = call.getString("locationAccuracy") ?? "best"
        let distanceFilter = call.getDouble("distanceFilter") ?? 5.0

        locationManager = CLLocationManager()
        locationManager?.delegate = self
        locationManager?.desiredAccuracy = accuracy == "best" ? kCLLocationAccuracyBestForNavigation : kCLLocationAccuracyBest
        locationManager?.distanceFilter = distanceFilter
        locationManager?.allowsBackgroundLocationUpdates = true
        locationManager?.pausesLocationUpdatesAutomatically = false

        locationManager?.requestAlwaysAuthorization()
        locationManager?.startUpdatingLocation()

        isTracking = true
        isPaused = false
        startTime = Date()
        totalDistance = 0
        trackPoints.removeAll()
        lastLocation = nil

        let outputPath = call.getString("outputPath") ?? defaultGpxPath()
        saveTrackingState(tracking: true, path: outputPath)

        startBackgroundTask()

        call.resolve([
            "success": true,
            "message": "Tracking started",
            "outputPath": outputPath
        ])
    }

    @objc public func stopTracking(_ call: CAPPluginCall) {
        guard isTracking else {
            call.resolve([
                "success": true,
                "gpxPath": NSNull(),
                "error": NSNull()
            ])
            return
        }

        locationManager?.stopUpdatingLocation()
        isTracking = false
        isPaused = false

        let outputPath = UserDefaults.standard.string(forKey: "\(stateKey)_output_path") ?? defaultGpxPath()
        let gpxSuccess = writeGPX(to: outputPath)

        let data: [String: Any] = [
            "success": true,
            "gpxPath": gpxSuccess ? outputPath : NSNull(),
            "error": gpxSuccess ? NSNull() : "Failed to write GPX",
            "distance_m": totalDistance,
            "duration_seconds": startTime.map { Date().timeIntervalSince($0) } ?? 0,
            "points": trackPoints.count
        ]

        clearTrackingState()
        stopBackgroundTask()

        call.resolve(data)
        notifyListeners("trackingStopped", data)
    }

    @objc public func pauseTracking(_ call: CAPPluginCall) {
        guard isTracking && !isPaused else {
            call.resolve(["success": true])
            return
        }
        isPaused = true
        locationManager?.stopUpdatingLocation()
        call.resolve(["success": true])
    }

    @objc public func resumeTracking(_ call: CAPPluginCall) {
        guard isTracking && isPaused else {
            call.resolve(["success": true])
            return
        }
        isPaused = false
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

    @objc public func readGpx(_ call: CAPPluginCall) {
        guard let path = call.getString("path") else {
            call.reject("Path is required")
            return
        }

        let url = URL(fileURLWithPath: path)
        guard let content = try? String(contentsOf: url) else {
            call.reject("Failed to read GPX file")
            return
        }

        call.resolve([
            "base64": content.toBase64()
        ])
    }

    @objc public func getTrackingState(_ call: CAPPluginCall) {
        let defaults = UserDefaults.standard
        let isTracking = defaults.bool(forKey: "\(stateKey)_is_tracking")
        let path = defaults.string(forKey: "\(stateKey)_output_path")
        call.resolve([
            "isTracking": isTracking,
            "outputPath": path ?? NSNull()
        ])
    }

    @objc public func clearTrackingState(_ call: CAPPluginCall) {
        clearTrackingState()
        call.resolve()
    }

    private func writeGPX(to path: String) -> Bool {
        let formatter = ISO8601DateFormatter()
        var xml = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BikeMaster-iOS" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>BikeMaster ride</name>
    <trkseg>
"""
        for point in trackPoints {
            xml += """
      <trkpt lat="\(point.lat)" lon="\(point.lon)">
        <ele>\(point.altitude)</ele>
        <time>\(formatter.string(from: point.timestamp))</time>
      </trkpt>
"""
        }
        xml += """
    </trkseg>
  </trk>
</gpx>
"""
        do {
            try xml.write(toFile: path, atomically: true, encoding: .utf8)
            return true
        } catch {
            return false
        }
    }

    private func startBackgroundTask() {
        backgroundTask = UIApplication.shared.beginBackgroundTask(withName: "BikeTracking") {
            self.stopBackgroundTask()
        }
    }

    private func stopBackgroundTask() {
        if backgroundTask != .invalid {
            UIApplication.shared.endBackgroundTask(backgroundTask)
            backgroundTask = .invalid
        }
    }

    public func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last, isTracking && !isPaused else { return }

        if let accuracy = location.horizontalAccuracy, accuracy > 20 {
            return
        }

        lastLocation = location

        if let previous = trackPoints.last {
            totalDistance += location.distance(from: CLLocation(latitude: previous.lat, longitude: previous.lon))
        }

        trackPoints.append((lat: location.coordinate.latitude, lon: location.coordinate.longitude, altitude: location.altitude, timestamp: location.timestamp))

        let data: [String: Any] = [
            "distance": totalDistance,
            "currentSpeed": location.speed * 3.6,
            "avgSpeed": trackPoints.count > 1 ? (totalDistance / 1000.0) / ((Date().timeIntervalSince(startTime ?? Date())) / 3600.0) : 0,
            "elapsedTime": startTime.map { Date().timeIntervalSince($0) } ?? 0,
            "elevation": location.altitude,
            "points": trackPoints.count,
            "isPaused": isPaused,
            "lastLatitude": location.coordinate.latitude,
            "lastLongitude": location.coordinate.longitude
        ]

        notifyListeners("trackingState", data)
    }

    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        notifyListeners("trackingStopped", [
            "error": error.localizedDescription,
            "gpxPath": NSNull()
        ])
    }

    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = CLLocationManager.authorizationStatus()
        notifyListeners("permissionChange", [
            "status": String(describing: status)
        ])
    }
}

extension String {
    func toBase64() -> String {
        return Data(self.utf8).base64EncodedString()
    }
}

CAP_PLUGIN(BikeTrackingPlugin, "BikeTracking", [
    "startTracking": [CAP_SINGLETON],
    "stopTracking": [CAP_SINGLETON],
    "pauseTracking": [CAP_SINGLETON],
    "resumeTracking": [CAP_SINGLETON],
    "checkPermissions": [CAP_SINGLETON],
    "readGpx": [CAP_SINGLETON],
    "getTrackingState": [CAP_SINGLETON],
    "clearTrackingState": [CAP_SINGLETON]
])
