#!/usr/bin/env bash
set -e

echo "=== BikeMaster iOS Setup ==="
echo ""
echo "Prerequisites:"
echo "  - macOS with Xcode 15+ installed"
echo "  - Node.js 18+"
echo "  - CocoaPods: sudo gem install cocoapods"
echo ""
echo "Step 1: Add iOS platform to Capacitor"
cd "$(dirname "$0")/.."
npx cap add ios
echo ""
echo "Step 2: Install iOS dependencies"
cd ios
pod install
cd ..
echo ""
echo "Step 3: Copy plugin files"
cp -r ios-copy/BikeTracking ios/App/
echo ""
echo "Step 4: Open Xcode workspace"
npx cap open ios
echo ""
echo "iOS project ready at: frontend/ios/"
echo ""
echo "Next steps in Xcode:"
echo "  1. Set team signing (Project -> Signing & Capabilities)"
echo "  2. Enable Background Modes: Location updates"
echo "  3. Set deployment target to iOS 16.0+"
echo "  4. Build and run on device (GPS requires real hardware)"
