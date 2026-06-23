package com.bikemaster;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import androidx.core.app.NotificationCompat;
import com.getcapacitor.Plugin;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

@CapacitorPlugin(
    name = "BikeTracking",
    permissions = {
        @Permission(strings = {"android.permission.ACCESS_COARSE_LOCATION"}, description = "GPS location for tracking rides"),
        @Permission(strings = {"android.permission.ACCESS_FINE_LOCATION"}, description = "Precise GPS location for ride tracking"),
        @Permission(strings = {"android.permission.ACCESS_BACKGROUND_LOCATION"}, description = "Background GPS for continuous tracking")
    }
)
public class TrackingService extends Service implements LocationListener {
    private static final String CHANNEL_ID = "bikemaster_tracking";
    private LocationManager locationManager;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            CharSequence name = "BikeMaster Tracking";
            String description = "GPS tracking for rides";
            int importance = NotificationManager.IMPORTANCE_LOW;
            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, name, importance);
            channel.setDescription(description);
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            notificationManager.createNotificationChannel(channel);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(1, createNotification());
        return START_STICKY;
    }

    private Notification createNotification() {
        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("BikeMaster Tracking")
            .setContentText("GPS tracking in progress...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onLocationChanged(Location location) {
        // Handle location updates
    }

    @Override
    public void onStatusChanged(String provider, int status, Bundle extras) {}

    @Override
    public void onProviderEnabled(String provider) {}

    @Override
    public void onProviderDisabled(String provider) {}
}