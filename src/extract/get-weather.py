import json
import requests
import boto3
from datetime import datetime, timezone
import logging
import os

# Define base directory and paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "cities.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define S3 bucket and prefix
S3_BUCKET = "cmcd-etl-weather-lake"  # replace with your bucket name
S3_PREFIX = "bronze/raw"

s3 = boto3.client("s3")

# Load city configuration
def load_cities():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

# Build the API URL for a given latitude and longitude
def build_url(lat, lon):
    base = "https://api.open-meteo.com/v1/forecast"
    params = (
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&hourly=temperature_2m,relativehumidity_2m,precipitation,"
        "wind_speed_10m,windgusts_10m,pressure_msl,uv_index,shortwave_radiation"
        "&timezone=UTC"
    )
    return base + params

# Upload data to S3
def upload_to_s3(data, city, ts):
    key = (
        f"{S3_PREFIX}/city={city}/year={ts:%Y}/month={ts:%m}/"
        f"day={ts:%d}/hour={ts:%H}/data.json"
    )

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(data),
        ContentType="application/json"
    )

    logging.info(f"Uploaded to s3://{S3_BUCKET}/{key}")

# Fetch weather data and upload to S3
def fetch_and_upload(city_info):
    city = city_info["city"]
    lat = city_info["lat"]
    lon = city_info["lon"]

    url = build_url(lat, lon)
    logging.info(f"Fetching weather data for {city}: {url}")

    response = requests.get(url)

    if response.status_code != 200:
        logging.error(f"Failed for {city}, status_code={response.status_code}")
        return

    data = response.json()
    ts = datetime.now(timezone.utc)

    upload_to_s3(data, city, ts)

# Main function to process all cities
def main():
    cities = load_cities()
    for city in cities:
        try:
            fetch_and_upload(city)
        except Exception as e:
            logging.error(f"Error processing {city['city']}: {e}")


if __name__ == "__main__":
    main()
