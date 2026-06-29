package com.bikemaster

import com.getcapacitor.BridgeActivity
import android.os.Bundle

class MainActivity : BridgeActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        registerPlugin(BikeTrackingPlugin::class.java)
    }
}