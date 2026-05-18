import requests

def get_daily_prayer_time(city_name):
    url = f"https://api.islam.com/v1/prayers?city={city_name}&method=json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError if the HTTP request was unsuccessful
        data = response.json()
        
        # Assuming the response contains prayer times, we extract them from the JSON
        prayer_times = {
            "Sunrise": data['data'][0]['fajr'],
            "Dhuhr": data['data'][1]['dhuhr'],
            "Asr": data['data'][2]['asr'],
            "Maghrib": data['data'][3]['maghrib'],
            "Isha": data['data'][4]['isha']
        }
        
        # Return the prayer times as a formatted string
        return f"Sunrise: {prayer_times['Sunrise']}\nDhuhr: {prayer_times['Dhuhr']}\nAsr: {prayer_times['Asr']}\nMaghrib: {prayer_times['Maghrib']}\nIsha: {prayer_times['Isha']}"
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        return f"An error occurred: {e}"

# Example usage
city_name = "istanbul"
print(get_daily_prayer_time(city_name))