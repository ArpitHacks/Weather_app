import streamlit as st
import requests
import json
from datetime import date, timedelta
from PIL import Image
import io

# --- 1. CONFIGURATION & STYLING ---
# Page configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Weather Checker",
    page_icon="🌦️",
    layout="centered",
    initial_sidebar_state="auto",
)

# Thresholds for adverse weather conditions
THRESHOLDS = {
    "VERY_HOT_C": 35.0,
    "VERY_COLD_C": 5.0,
    "VERY_WINDY_KMH": 40.0,
    "VERY_WET_PROBABILITY": 60,
    "UNCOMFORTABLE_APPARENT_TEMP_C": 38.0
}

# --- 2. API HELPER FUNCTIONS ---

# Use Streamlit's caching to store results and avoid re-calling APIs with the same inputs
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_coordinates(location_name):
    """Converts a location name into latitude and longitude using Nominatim."""
    try:
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {'q': location_name, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'WeatherWebApp/1.0 (Streamlit)'}
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data:
            return None, None
        return float(data[0]['lat']), float(data[0]['lon'])
    except requests.exceptions.RequestException as e:
        st.error(f"Geocoding API Error: Could not connect. Please check your internet connection.")
        return None, None
    except (IndexError, json.JSONDecodeError):
        return None, None # Location not found or bad response

@st.cache_data(ttl=600) # Cache weather data for 10 minutes
def get_weather_likelihood(latitude, longitude, forecast_date):
    """Fetches and analyzes weather data from Open-Meteo."""
    try:
        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "auto",
            "start_date": forecast_date,
            "end_date": forecast_date
        }
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        daily_data = data.get('daily', {})

        # Extract data with fallbacks
        max_temp = daily_data.get('temperature_2m_max', [None])[0]
        min_temp = daily_data.get('temperature_2m_min', [None])[0]
        apparent_temp_max = daily_data.get('apparent_temperature_max', [None])[0]
        wind_speed_max = daily_data.get('wind_speed_10m_max', [None])[0]
        precip_prob_max = daily_data.get('precipitation_probability_max', [None])[0]

        if any(v is None for v in [max_temp, min_temp, apparent_temp_max, wind_speed_max, precip_prob_max]):
            return {"error": "Weather data from API was incomplete."}

        # Analyze conditions against thresholds
        adverse_conditions = []
        if max_temp > THRESHOLDS["VERY_HOT_C"]:
            adverse_conditions.append(f"☀️ **Very Hot:** Up to {max_temp}°C")
        if min_temp < THRESHOLDS["VERY_COLD_C"]:
            adverse_conditions.append(f"🥶 **Very Cold:** Down to {min_temp}°C")
        if wind_speed_max > THRESHOLDS["VERY_WINDY_KMH"]:
            adverse_conditions.append(f"💨 **Very Windy:** Up to {wind_speed_max} km/h")
        if precip_prob_max >= THRESHOLDS["VERY_WET_PROBABILITY"]:
            adverse_conditions.append(f"💧 **Very Wet:** {precip_prob_max}% chance of rain")
        if apparent_temp_max > THRESHOLDS["UNCOMFORTABLE_APPARENT_TEMP_C"]:
            adverse_conditions.append(f"🥵 **Uncomfortable:** Feels like {apparent_temp_max}°C")

        return {
            "forecast": {
                "Max Temp": f"{max_temp}°C",
                "Min Temp": f"{min_temp}°C",
                "Max Wind": f"{wind_speed_max} km/h",
                "Rain Chance": f"{precip_prob_max}%"
            },
            "adverse_conditions_found": adverse_conditions
        }
    except requests.exceptions.RequestException:
        st.error("Weather API Error: Could not connect. Please check your internet connection.")
        return {"error": "API connection failed."}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# --- 3. STREAMLIT UI ---

st.title("Will It Rain On My Parade?")
st.markdown("Enter a location to check for adverse weather conditions for an event **5 days from now**.")

# User input for location name
location_input = st.text_input("Enter a location name", "Bhubaneswar, India", placeholder="e.g., Eiffel Tower, Paris")

if st.button("Check Weather Conditions", type="primary"):
    if location_input:
        with st.spinner(f"Finding '{location_input}' and checking the skies..."):
            # Step 1: Get coordinates
            lat, lon = get_coordinates(location_input)

            if lat is not None and lon is not None:
                # Step 2: Get weather if coordinates are found
                target_date = date.today() + timedelta(days=5)
                date_str = target_date.strftime("%Y-%m-%d")
                analysis = get_weather_likelihood(lat, lon, date_str)

                st.subheader(f"Analysis for {location_input.title()} on {date_str}")

                if "error" in analysis:
                    st.error(analysis['error'])
                else:
                    # Display forecast data using columns and metrics for a dashboard look
                    st.info("#### Forecast Summary")
                    col1, col2 = st.columns(2)
                    col1.metric("Max Temperature", analysis['forecast']['Max Temp'])
                    col2.metric("Min Temperature", analysis['forecast']['Min Temp'])
                    col1.metric("Max Wind Speed", analysis['forecast']['Max Wind'])
                    col2.metric("Rain Probability", analysis['forecast']['Rain Chance'])

                    st.divider()

                    # Display adverse conditions analysis
                    if analysis['adverse_conditions_found']:
                        st.warning("#### ⚠️ Adverse Conditions Likely")
                        for condition in analysis['adverse_conditions_found']:
                            st.markdown(f"- {condition}")
                    else:
                        st.success("#### ✅ Looks Good! No significant adverse conditions detected.")
            else:
                st.error(f"Could not find coordinates for '{location_input}'. Please try a different or more specific location.")
    else:
        st.warning("Please enter a location.")

st.markdown("---")
st.markdown("Powered by [Open-Meteo](https://open-meteo.com/) and [OpenStreetMap](https://www.openstreetmap.org).")
