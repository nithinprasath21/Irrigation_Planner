import os
import json
import pandas as pd
import streamlit as st
import requests
from groq import Groq
import re

# Streamlit page configuration with increased display width
st.set_page_config(
    page_title="Irrigation Scheduler",
    page_icon="🌾",
    layout="wide"  # Increased width for better display
)

# Load API Key and initialize Groq client
working_dir = os.path.dirname(os.path.abspath(__file__))
config_data = json.load(open(f"{working_dir}/config.json"))

GROQ_API_KEY = config_data["GROQ_API_KEY"]
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

client = Groq()

# Initialize chat history and first iteration flag in Streamlit session state if not already present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_first_iteration" not in st.session_state:
    st.session_state.is_first_iteration = False
if "assistant_response" not in st.session_state:
    st.session_state.assistant_response = ""
if "irrigation_data" not in st.session_state:
    st.session_state.irrigation_data = []

# Define the long system prompt including single time slot requirement
system_prompt = (
    "You are an irrigation scheduling assistant. For every request, you must generate a 5-day irrigation schedule for any given crop. "
    "Each day should include a single preferred time slot based on rainfall prediction. Ensure that the output is in the following tabular format with fixed attributes for all crops. Each day's schedule should include the following columns:\n\n"
    "1. Day - The day of the schedule (1-5).\n"
    "2. Time Slot - The preferred time slot for watering based on rainfall prediction (e.g., Morning, Evening).\n"
    "3. Watering Depth - The depth of watering in cm.\n"
    "4. Water Volume per Hour - The amount of water applied per hour in liters.\n"
    "5. Total Water Volume - The total amount of water applied for the time slot in liters.\n"
    "6. Additional Tips - Any additional tips or recommendations related to irrigation.\n\n"
    "The generated output must be structured in the following tabular format:\n\n"
    "| Day | Time Slot | Watering Depth (cm) | Water Volume per Hour (liters) | Total Water Volume (liters) | Additional Tips |\n"
    "|-----|-----------|---------------------|-------------------------------|----------------------------|-----------------|\n"
    "| 1   | Morning    | 2.5                 | 750                           | 7,500                      | Tip example      |\n"
    "| 2   | Evening    | 1.5                 | 500                           | 4,000                      | Tip example      |\n"
    "| 3   | Morning    | 3.0                 | 1,000                         | 12,000                     | Tip example      |\n"
    "| 4   | Evening    | 2.0                 | 750                           | 6,000                      | Tip example      |\n"
    "| 5   | Morning    | 2.0                 | 750                           | 6,000                      | Tip example      |\n\n"
    "Additional Requirements:\n\n"
    "- Ensure that the total water volume for each day is provided by the amount of water applied in the preferred time slot.\n"
    "- Display the final output in a tabular format in your response.\n\n"
    "All generated results must follow this format and include the same attributes dynamically. Maintain consistency in the structure and attributes for every crop."
)

# Streamlit page title
st.title("🌾 Irrigation Scheduling ChatBot")

# Weather API key and URL
WEATHER_API_KEY = "4c4b7420a738501346b47167ab5f7f10"
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"

# Function to fetch weather data based on location
def get_weather(location):
    params = {
        "q": location,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }
    response = requests.get(WEATHER_API_URL, params=params)
    data = response.json()
    if response.status_code == 200:
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        return temperature, humidity
    else:
        st.error("Could not fetch weather data.")
        return None, None

# Inject custom CSS for smaller blinking LED
st.markdown(
    """
    <style>
    .blinking-led {
        width: 8px;  /* Smaller size */
        height: 8px;
        background-color: green;
        border-radius: 50%;
        display: inline-block;
        animation: blinking 1s infinite;
    }
    @keyframes blinking {
        0% { opacity: 1.0; }
        50% { opacity: 0.3; }
        100% { opacity: 1.0; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# First iteration: Collecting irrigation data
with st.form(key='irrigation_form'):
    crop_type = st.text_input("Enter the crop type (e.g., wheat, rice, maize)", value="carrot")
    soil_type = st.selectbox("Select the soil type", ["Alluvial", "Black", "Red", "Laterite", "Desert", "Mountain"], index=0)
    location = st.text_input("Enter your location (e.g., city, region)", value="Coimbatore")
    land_size = st.number_input("Enter the land size (in acres)", min_value=0.1, step=0.1, value=0.5)
    
    # Button at the bottom of the form
    submit_data_button = st.form_submit_button("Submit Data")

# Check if the "Submit Data" button is clicked
if submit_data_button:
    # Fetch weather data
    temperature, humidity = get_weather(location)

    # Display temperature and humidity with green blinking LED
    if temperature is not None and humidity is not None:
        st.write(f"### Current Weather Data in {location}")
        st.markdown(f"<div>Temperature: {temperature}°C <span class='blinking-led'></span></div>", unsafe_allow_html=True)
        st.markdown(f"<div>Humidity: {humidity}% <span class='blinking-led'></span></div>", unsafe_allow_html=True)

    # Formulate the prompt including weather data
    user_prompt = (f"Provide a 5-day irrigation schedule for {crop_type} crop in {soil_type} soil, "
                   f"located in {location}, with a land size of {land_size} acres. The current temperature is {temperature}°C "
                   f"and the humidity is {humidity}%. Include water irrigation techniques, strategies, timings, and the amount of water "
                   f"required in liters for each day, broken down by the preferred time slot based on rainfall prediction, and provide insights based on the weather conditions.")

    # Append user prompt to chat history
    st.chat_message("user").markdown(user_prompt)
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})

    # Send user's message to the LLM and get a response
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Use the appropriate model
        messages=messages
    )

    st.session_state.assistant_response = response.choices[0].message.content
    st.session_state.chat_history.append({"role": "assistant", "content": st.session_state.assistant_response})

    # Display the LLM's response
    with st.chat_message("assistant"):
        st.markdown(st.session_state.assistant_response)

    # Set the flag for the first iteration
    st.session_state.is_first_iteration = True

# Display results after the first iteration
if st.session_state.is_first_iteration:
    try:
        # Improved regex to handle potential formatting issues
        matches = re.findall(
            r"Day (\d+)\s+Time Slot\s+(.+?)\s+Watering Depth\s+(.+?)\s+Water Volume per Hour\s+(.+?)\s+Total Water Volume\s+(.+?)\s+Additional Tips\s+(.+)", 
            st.session_state.assistant_response, 
            re.DOTALL
        )
        
        # Convert matches to a list of dictionaries
        irrigation_data = []
        for day, time_slot, depth, volume_per_hour, total_volume, tips in matches:
            irrigation_data.append({
                "Day": int(day),
                "Time Slot": time_slot,
                "Watering Depth (cm)": float(depth),
                "Water Volume per Hour (liters)": float(volume_per_hour),
                "Total Water Volume (liters)": float(total_volume),
                "Additional Tips": tips.strip()
            })

        # Save irrigation data to session state
        st.session_state.irrigation_data = irrigation_data
        
    except Exception as e:
        st.error(f"Error processing the assistant's response: {e}")
