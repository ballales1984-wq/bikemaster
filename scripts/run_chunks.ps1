$ErrorActionPreference = 'Continue'
$root = 'D:\BikeMaster'
$groups = @(
  @('tests/test_advanced_analytics.py','tests/test_analytics_engine.py','tests/test_analytics_trends.py','tests/test_analytics_gaps.py','tests/test_analytics_context_builder.py'),
  @('tests/test_power_model.py','tests/test_performance_calculator.py','tests/test_core_power_calculator.py','tests/test_core_calculators.py','tests/test_core_physics.py','tests/test_core_physics_validation.py','tests/test_core_fatigue.py','tests/test_core_models.py','tests/test_validation.py','tests/test_engine.py','tests/test_pipeline.py','tests/test_models.py'),
  @('tests/test_routes_integration.py','tests/test_routes_minimal.py','tests/test_routes_extended.py','tests/test_api_coverage.py','tests/test_main.py','tests/test_security.py','tests/test_auth_enhanced.py','tests/test_dashboard_auth.py','tests/test_google_auth.py','tests/test_google_oauth.py','tests/test_google_oauth_store.py'),
  @('tests/test_ai_coach.py','tests/test_ai_coach_api.py','tests/test_knowledge_api.py','tests/test_poi_api.py','tests/test_scores_api.py','tests/test_speed_path_api.py','tests/test_benchmark_api.py','tests/test_athlete_profile.py','tests/test_fitness_state.py','tests/test_fitness_state_repository.py','tests/test_badges.py'),
  @('tests/test_bm2_engine.py','tests/test_bm2_api.py','tests/test_bm2_units.py','tests/test_bm2_models.py','tests/test_bm2_agents.py','tests/test_bm2_routes_integration.py','tests/test_bm2_ride_adapter.py'),
  @('tests/test_strava_integration.py','tests/test_strava_client_unit.py','tests/test_garmin_integration.py','tests/test_google_fit.py','tests/test_google_health.py','tests/test_wahoo_client.py','tests/test_import_batch.py'),
  @('tests/test_traffic.py','tests/test_traffic_client.py','tests/test_traffic_safety.py','tests/test_weather.py','tests/test_weather_service.py','tests/test_gps_parser.py','tests/test_gps_compression.py','tests/test_serpapi_maps.py','tests/test_google_maps_mock.py'),
  @('tests/test_event_bus.py','tests/test_events.py','tests/test_tracing.py','tests/test_tracing_more.py','tests/test_observability.py','tests/test_redis_client.py','tests/test_rate_limiter.py','tests/test_task_queue.py','tests/test_task_queue_more.py','tests/test_task_queue_extra.py','tests/test_task_queue_unit.py'),
  @('tests/test_audit.py','tests/test_audit_log.py','tests/test_database_backup.py','tests/test_logging_config.py','tests/test_config.py','tests/test_package_init.py','tests/test_repositories.py','tests/test_processing.py','tests/test_training_plan_generator.py','tests/test_training_stress.py','tests/test_training_load.py'),
  @('tests/test_anomaly_detection.py','tests/test_vip_predictor.py','tests/test_multi_classifier.py','tests/test_ride_route_estimator.py','tests/test_inactivity_estimator.py','tests/test_segment_detector.py','tests/test_granfondo.py','tests/test_ride_analysis_service.py','tests/test_dashboard.py','tests/test_dashboard_scores.py','tests/test_frontend_dashboard.py','tests/test_proactive_assistant.py','tests/test_adaptation_engine.py','tests/test_schemas_validation.py'),
  @('bike_analyzer/tests','aethermap/src/tests')
)
$i = 0
foreach ($g in $groups) {
  $i++
  $f = Join-Path $root "chunk_$i.log"
  $e = Join-Path $root "chunk_$i.err"
  $args = @('-m','pytest') + $g + @('-q','-p','no:cacheprovider')
  Start-Process -FilePath python -ArgumentList $args -WorkingDirectory $root -RedirectStandardOutput $f -RedirectStandardError $e -NoNewWindow -PassThru | ForEach-Object { $_.Id } | Out-File -FilePath (Join-Path $root "chunk_$i.pid") -Encoding ascii
}
Write-Host "Launched $i chunks"
