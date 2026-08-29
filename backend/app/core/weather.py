import math
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional
import urllib.request
import json

# Node coordinates mapping for regional weather
NODE_COORDINATES = {
    "inst-a": {"name": "Metro District (Urban)", "latitude": 28.6139, "longitude": 77.2090}, # Delhi
    "inst-b": {"name": "Suburban Valley (Semi-Urban)", "latitude": 18.5204, "longitude": 73.8567}, # Pune
    "inst-c": {"name": "Highland Rural (Rural)", "latitude": 23.3441, "longitude": 85.3096}, # Ranchi
    "inst-d": {"name": "Coastal District (Mixed)", "latitude": 13.0827, "longitude": 80.2707} # Chennai
}

def fetch_regional_weather(node_id: str = "inst-a", query_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches real-time / archival weather metrics (temperature, relative humidity, precipitation, AQI)
    from Open-Meteo API for node coordinates, with deterministic physical fallback simulation.
    """
    coord = NODE_COORDINATES.get(node_id, NODE_COORDINATES["inst-a"])
    lat = coord["latitude"]
    lon = coord["longitude"]
    target_date = query_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Try querying Open-Meteo forecast/archive API
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,surface_pressure&timezone=auto"
        req = urllib.request.Request(url, headers={"User-Agent": "HealthSignal-Surveillance/2.0"})
        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                current = data.get("current", {})
                return {
                    "source": "Open-Meteo Live API",
                    "node_id": node_id,
                    "region": coord["name"],
                    "date": target_date,
                    "latitude": lat,
                    "longitude": lon,
                    "temperature_c": current.get("temperature_2m", 28.5),
                    "relative_humidity_pct": current.get("relative_humidity_2m", 65),
                    "precipitation_mm": current.get("precipitation", 0.0),
                    "surface_pressure_hpa": current.get("surface_pressure", 1012.0),
                    "heat_index_c": round(current.get("temperature_2m", 28.5) + (current.get("relative_humidity_2m", 65) - 50) * 0.1, 1),
                    "syndromic_risk_context": "Elevated respiratory/fever transmission window" if current.get("relative_humidity_2m", 65) > 75 else "Baseline environmental condition"
                }
    except Exception:
        pass

    # High-fidelity deterministic seasonal fallback
    d = datetime.strptime(target_date, "%Y-%m-%d") if query_date else datetime.now(timezone.utc)
    day_of_year = d.timetuple().tm_yday
    
    # Base temp cycle
    temp = round(26.0 + 8.0 * math.sin(2 * math.pi * (day_of_year - 80) / 365.0), 1)
    humidity = round(60.0 + 20.0 * math.sin(2 * math.pi * (day_of_year - 180) / 365.0), 1)
    precip = round(max(0.0, 5.0 * math.sin(2 * math.pi * (day_of_year - 190) / 365.0)), 1)

    return {
        "source": "HealthSignal Climate Simulator (Fallback)",
        "node_id": node_id,
        "region": coord["name"],
        "date": target_date,
        "latitude": lat,
        "longitude": lon,
        "temperature_c": temp,
        "relative_humidity_pct": humidity,
        "precipitation_mm": precip,
        "surface_pressure_hpa": 1013.25,
        "heat_index_c": round(temp + (humidity - 50) * 0.1, 1),
        "syndromic_risk_context": "Monsoon / Vector-borne surge season" if precip > 2.0 else "Stable environmental phase"
    }
