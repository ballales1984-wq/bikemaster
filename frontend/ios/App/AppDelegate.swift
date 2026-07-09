import UIKit
import Capacitor

@main
class AppDelegate: UIResponder, UIApplicationDelegate, CAPBridgeDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        return true
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }

    func makeBridge(with configuration: CAPBridgeConfig) -> CAPBridge {
        let bridge = CAPBridge(configuration: configuration)
        return bridge
    }
}
