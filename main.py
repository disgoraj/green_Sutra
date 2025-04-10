from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
import pandas as pd
import google.generativeai as genai
import requests
from dotenv import load_dotenv
import os
from typing import Optional
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI()
@app.on_event("startup")
async def startup_event():
    global df
    # Load dataset (assume it's already present locally)
    try:
        df = pd.read_csv('updated_india_agri_data.csv')
        print("Dataset loaded successfully")
    except FileNotFoundError as e:
        print(f"Error loading dataset: {str(e)}")
        raise FileNotFoundError("updated_india_agri_data.csv not found in the current directory. Please upload it manually.")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates for rendering HTML
templates = Jinja2Templates(directory="templates")

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB3x4u31dwLrgTNMLNeb9LWNAJiurinzfA")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "4761e19fa1d5f0e73042f23050507d45")

# Configure Gemini API
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-pro')
    print("Gemini API configured successfully")
except Exception as e:
    print(f"Error configuring Gemini API: {str(e)}")
    raise RuntimeError(f"Failed to configure Gemini API: {str(e)}")

# Emoji mapping for output
emoji_map = {
    "Next Crop": "🌾",
    "Weather": "☁️",
    "Water Needed": "💧",
    "Fertilizer Needed": "🌿",
    "Protect Crops": "🛡️",
    "Limited Resources": "♻️",
    "Disease Prevention Tip": "🩺",
    "Accuracy": "📊",
    "Suggestion": "💡"
}

# Mapping of states to major cities for weather API
STATE_TO_CITY = {
    "Andaman and Nicobar Islands": "Port Blair",
    "Andhra Pradesh": "Amaravati",
    "Arunachal Pradesh": "Itanagar",
    "Assam": "Dispur",
    "Bihar": "Patna",
    "Chandigarh": "Chandigarh",
    "Chhattisgarh": "Raipur",
    "Dadra and Nagar Haveli": "Silvassa",
    "Daman and Diu": "Daman",
    "Delhi": "New Delhi",
    "Goa": "Panaji",
    "Gujarat": "Gandhinagar",
    "Haryana": "Chandigarh",
    "Himachal Pradesh": "Shimla",
    "Jammu and Kashmir": "Srinagar (Summer), Jammu (Winter)",
    "Jharkhand": "Ranchi",
    "Karnataka": "Bengaluru",
    "Kerala": "Thiruvananthapuram",
    "Ladakh": "Leh",
    "Madhya Pradesh": "Bhopal",
    "Maharashtra": "Mumbai",
    "Manipur": "Imphal",
    "Meghalaya": "Shillong",
    "Mizoram": "Aizawl",
    "Nagaland": "Kohima",
    "Odisha": "Bhubaneswar",
    "Puducherry": "Puducherry",
    "Punjab": "Chandigarh",
    "Rajasthan": "Jaipur",
    "Sikkim": "Gangtok",
    "Tamil Nadu": "Chennai",
    "Telangana": "Hyderabad",
    "Tripura": "Agartala",
    "Uttar Pradesh": "Lucknow",
    "Uttarakhand": "Dehradun",
    "West Bengal": "Kolkata"
}

# Function to fetch live weather data
def fetch_weather(location: str) -> dict:
    city = STATE_TO_CITY.get(location, location)
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={OPENWEATHER_API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"Weather data for {city}: {data}")
            return {
                "temperature": data["main"]["temp"],
                "rainfall": data.get("rain", {}).get("1h", 0)
            }
        else:
            print(f"Weather API failed for {city}: Status Code {response.status_code}, Response: {response.text}")
            return {"temperature": 25, "rainfall": 2}
    except Exception as e:
        print(f"Error fetching weather for {city}: {str(e)}")
        return {"temperature": 25, "rainfall": 2}

# Function to recommend crop based on CSV lookup
def recommend_crop(user_input: dict) -> tuple[str, float]:
    try:
        # Simple lookup based on state and soil type (example logic)
        matching_rows = df[
            (df['State'] == user_input['State']) & 
            (df['Soil Type'] == user_input['Soil Type'])
        ]
        if not matching_rows.empty:
            row = matching_rows.iloc[0]
            predicted_crop = row['Recommend Crop']
            # Dummy confidence (since no model)
            max_prob = 85.0  # Placeholder confidence
            print(f"Recommended crop: {predicted_crop}, Confidence: {max_prob}%")
            return predicted_crop, max_prob
        else:
            # Fallback to a default crop
            default_crop = df['Recommend Crop'].iloc[0]
            print(f"No match found, defaulting to: {default_crop}")
            return default_crop, 75.0
    except Exception as e:
        print(f"Error in recommend_crop: {str(e)}")
        return "Unknown", 50.0

# Route to handle favicon request (fixes 404 error)
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)  # No Content

# Route to serve the HTML form
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route to handle form submission and provide advice
@app.post("/get_advice", response_class=HTMLResponse)
async def get_advice(
    request: Request,
    state: str = Form(...),
    soil_type: str = Form(...),
    previous_crop: str = Form(...),
    fertilizer_used: str = Form(...),
    water_hardness: str = Form(...),
    livestock: str = Form(...),
    resources: str = Form(...)
):
    try:
        # Log the received form data
        print(f"Received form data: state={state}, soil_type={soil_type}, previous_crop={previous_crop}, "
              f"fertilizer_used={fertilizer_used}, water_hardness={water_hardness}, livestock={livestock}, resources={resources}")

        # Fetch live weather data
        weather_data = fetch_weather(state)
        temperature = weather_data["temperature"]
        rainfall = weather_data["rainfall"]

        # Prepare user input for recommendation
        user_input = {
            'State': state,
            'Soil Type': soil_type,
            'Previous Crop': previous_crop,
            'Fertilizer Used': fertilizer_used,
            'Water Hardness': water_hardness,
            'Livestock': livestock,
            'Resources': resources,
            'Temperature': temperature,
            'Rainfall': rainfall
        }

        # Recommend crop based on CSV lookup
        predicted_crop, max_prob = recommend_crop(user_input)

        # Prepare prompt for Gemini API
        prompt = (
            f"Given the following agricultural conditions:\n"
            f"State: {user_input['State']}\n"
            f"Soil Type: {user_input['Soil Type']}\n"
            f"Previous Crop: {user_input['Previous Crop']}\n"
            f"Fertilizer Used: {user_input['Fertilizer Used']}\n"
            f"Water Hardness: {user_input['Water Hardness']}\n"
            f"Livestock: {user_input['Livestock']}\n"
            f"Resources: {user_input['Resources']}\n"
            f"Temperature: {temperature}°C\n"
            f"Rainfall: {rainfall} mm\n"
            f"Recommended Crop: {predicted_crop}\n"
            f"Model Confidence: {max_prob:.1f}%\n"
            "Provide a detailed recommendation in this format:\n"
            "Recommended Crop: [crop name]\n"
            "Required Water: [amount] liters/day\n"
            "Required Fertilizer: [fertilizer type]\n"
            "Crop Protection Tip: [protection tip]\n"
            "Limited Resources Tip: [resource tip]\n"
            "Disease Prevention Tip: [prevention tip]\n"
            "If the model confidence is below 83%, provide suggestions:\n"
            "Suggestions:\n"
            "- [suggestion with **key points** in bold]\n"
            "- [suggestion with **key points** in bold]\n"
            "Suggestions: [list of suggestions, one per line]"
        )

        # Call Gemini APIs
        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()
        print(f"Gemini API response: {response_text}")

        # Parse Gemini response and clean up
        result = {}
        accuracy = max_prob
        suggestions = []
        parsing_suggestions = False
        for line in response_text.split('\n'):
            if line.strip().startswith("Suggestions:"):
                parsing_suggestions = True
                continue
            if parsing_suggestions:
                if line.strip():
                    # Preserve bold text by converting **text** to <span class="bold-green">text</span>
                    if "model confidence" in line.lower() or "%" in line:
                        continue
                    cleaned_suggestion = line.strip().lstrip('*-').strip()
                    import re
                    cleaned_suggestion = re.sub(r'\*\*(.*?)\*\*', r'<span class="bold-green">\1</span>', cleaned_suggestion)
                    suggestions.append(cleaned_suggestion)
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key == 'Recommended Crop':
                    value = value.split('(')[0].strip()
                    result['Recommend Crop'] = value
                elif key == 'Required Water':
                    result['Required Water'] = value
                elif key == 'Required Fertilizer':
                    result['Required Fertilizer'] = value
                elif key == 'Crop Protection Tip':
                    result['Crop Protection Tip'] = value
                elif key == 'Limited Resources Tip':
                    result['Limited Resources Tip'] = value
                elif key == 'Disease Prevention Tip':
                    result['Disease Prevention Tip'] = value

        # Log the processed suggestions
        print(f"Processed suggestions:\n{suggestions}")
        # Fill in missing fields from dataset
        if not all(key in result for key in ['Recommend Crop', 'Required Water', 'Required Fertilizer', 'Crop Protection Tip', 'Limited Resources Tip', 'Disease Prevention Tip']):
            match = df[df['Recommend Crop'] == predicted_crop].iloc[0]
            for key in ['Recommend Crop', 'Required Water', 'Required Fertilizer', 'Crop Protection Tip', 'Limited Resources Tip', 'Disease Prevention Tip']:
                if key not in result:
                    result[key] = str(match[key])

        # Prepare recommendation items for the template
        recommendation_items = [
            {"emoji": emoji_map["Next Crop"], "label": "Next Crop", "value": result['Recommend Crop']},
            {"emoji": emoji_map["Weather"], "label": "Current Weather", "value": f"{temperature}°C, {rainfall} mm rainfall"},
            {"emoji": emoji_map["Water Needed"], "label": "Water Needed", "value": result['Required Water']},
            {"emoji": emoji_map["Fertilizer Needed"], "label": "Fertilizer Needed", "value": result['Required Fertilizer']},
            {"emoji": emoji_map["Protect Crops"], "label": "Protect Crops", "value": result['Crop Protection Tip']},
            {"emoji": emoji_map["Limited Resources"], "label": "Limited Resources", "value": result['Limited Resources Tip']},
            {"emoji": emoji_map["Disease Prevention Tip"], "label": "Disease Prevention Tip", "value": result['Disease Prevention Tip']},
        ]

        # Render the result page
        return templates.TemplateResponse("result.html", {
            "request": request,
            "recommendation_items": recommendation_items,
            "suggestions": suggestions if accuracy < 83.0 else [],
            "error": None
        })

    except Exception as e:
        print(f"Error in get_advice: {str(e)}")
        return templates.TemplateResponse("result.html", {
            "request": request,
            "recommendation_items": [],
            "suggestions": [],
            "error": str(e)
        })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8800))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)