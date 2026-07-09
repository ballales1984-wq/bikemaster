#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required"
  exit 1
fi

if ! command -v pod >/dev/null 2>&1; then
  echo "CocoaPods (pod) is required"
  exit 1
fi

echo "Building web assets..."
npm run build

echo "Syncing Capacitor iOS..."
npx cap sync ios

echo "Installing CocoaPods dependencies..."
cd ios/App
pod install
cd ../..

echo "Opening Xcode workspace..."
open ios/App.xcworkspace
