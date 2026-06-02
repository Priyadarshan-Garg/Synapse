"""This class is responsible for fetching weather data from an external API.
It uses the OpenWeatherMap API to retrieve current weather conditions for a given city."""

import os
import json
import sys
import requests

class Wheather_Engine:
    def __init__(self):
        # Production ready: Store data in user's home directory
        user_home = os.path.expanduser("~")
        self.BASE_DIR = os.path.join(user_home, ".naina_ai")
        os.makedirs(self.BASE_DIR, exist_ok=True)
        self.config_file = os.path.join(self.BASE_DIR, "config.json")

        self.api_key = self._get_api_key()
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"

    def _get_api_key(self):
        # Default key (If you want to keep yours, otherwise replace with empty string "")
        default_key = "api_key"
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    return config.get("openweathermap_api_key", default_key)
            except Exception:
                return default_key
        else:
            # Create default config file if it doesn't exist
            try:
                with open(self.config_file, "w") as f:
                    json.dump({"openweathermap_api_key": default_key}, f, indent=4)
            except Exception:
                pass
            return default_key

    def get_weather(self, city):
        if not self.api_key or self.api_key == "":
            return "Weather API key is not configured. Please add it to your configuration file."
            
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric', # -> Tempreature celsius mein aayega isse
            'lang': 'en'       # -> Language english
        }
        
        print(f"\n [Fetching] weather data for: {city}...")
        
        try:
            # 5 second ka timeout laga diya. Agar internet nahi chala, to turant error dega aur app hang nahi hogi.
            response = requests.get(self.base_url, params=params, timeout=5) # -> Servers se data le rhe hain,Json format mein
            data = response.json()

            if data["cod"] == 200:
                # -> Data lenge aur display karenge
                temp = data['main']['temp']
                desc = data['weather'][0]['description']
                
                # -> (Precipitation, Wind, Humidity)
                humidity = data['main']['humidity']
                wind_speed = data['wind']['speed']
                
                # -> Rain ka data optional hai..
                rain = data.get('rain', {}).get('1h', 0) 

                print("-" * 30)
                print(f" Success! Weather in {city.capitalize()}:")
                print(f"[Temperature] : {temp}°C")
                print(f"[Condition] : {desc.title()}")
                print(f"[Humidity] : {humidity}%")
                print(f"[Wind Speed] : {wind_speed} m/s")
                
                if rain > 0:
                    print(f"[Precipitation] (last 1h): {rain} mm")
                else:
                    print(f"[Precipitation]: No rain reported.")
                print("-" * 30)
                
                # **ADD THIS RETURN STATEMENT:**
                return f"Temperature: {temp}°C, Condition: {desc.title()}, Humidity: {humidity}%, Wind: {wind_speed} m/s"
                
            else:
                print(f"[Error]: {data['message']}")
                return f"[Unavailable] : Weather data not available for {city}. Error: {data['message']}"
                
        except Exception as e:
            print(f"Something went wrong: {e}")
            return f"Failed to get weather data for {city}. Error: {e}"

# -> User se input leke weather check karenge
if __name__ == "__main__":
    bot = Wheather_Engine()  # Fixed class name here too
    city = input("Enter City Name: ")
    result = bot.get_weather(city)
    print(f"Returned: {result}")