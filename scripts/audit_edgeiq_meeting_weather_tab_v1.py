from edgeiq_meeting_workspace_audit_common_v1 import CSS, MEETING, WEATHER, read, run_audit

source = read(MEETING) + "\n" + read(WEATHER)
css = read(CSS)
checks = {
    "official_weather_service": "getMeetingWeather" in source,
    "no_radar": "radar" not in source.lower(),
    "no_forecast_confidence": "Forecast Confidence" not in source and "confidence bar" not in source.lower(),
    "summary_fields": all(text in source for text in ["Temperature", "Humidity", "Wind", "Rainfall", "Provider"]),
    "source_retained": "SourceStatus" in source and "source_status" in source,
    "unavailable_state": "Official weather data is not available for this meeting." in source,
    "light_theme": ".eiq-product-shell-v4 .eiq-metro-weather" in css and "#ffffff" in css,
}
run_audit("EDGEIQ_MEETING_WEATHER_TAB_V1", "EDGEIQ_MEETING_WEATHER_TAB_V1_AUDIT_PASS", checks, "edgeiq_meeting_weather_tab_v1_audit")
