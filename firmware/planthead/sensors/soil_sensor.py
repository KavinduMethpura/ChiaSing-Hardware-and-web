"""
Reads the STEMMA soil sensor over I2C every SOIL_INTERVAL_SEC and:
    1. Prints the reading locally with a full date/time stamp
    2. Appends it as a row to a local CSV file (permanent local dataset,
       survives even if Adafruit IO is unreachable or rate-limited)
    3. Uploads moisture + temperature to Adafruit IO

Run standalone to test just this piece:
    python3 -m sensors.soil_sensor
"""
import csv
import os
import time
import logging
from datetime import datetime

import board
from adafruit_seesaw.seesaw import Seesaw

import config
from io_client import send

logger = logging.getLogger("planthead.soil_sensor")

CSV_PATH = os.path.join(config.CAMERA_SAVE_DIR.rsplit("/", 1)[0], "soil_log.csv")
# resolves to "data/soil_log.csv" given CAMERA_SAVE_DIR = "data/images"


def init_sensor(addr=config.SOIL_SENSOR_ADDR):
    i2c = board.I2C()
    return Seesaw(i2c, addr=addr)


def read_once(ss):
    """Return (moisture, temperature_c) from one sensor."""
    moisture = ss.moisture_read()
    temp = ss.get_temp()
    return moisture, temp


def init_csv():
    """Create the CSV with a header row if it doesn't exist yet."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "time", "moisture", "temperature_c"])
        logger.info(f"Created new soil log at {CSV_PATH}")


def log_to_csv(date_str, time_str, moisture, temp):
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([date_str, time_str, moisture, round(temp, 2)])


def run_loop():
    ss = init_sensor()
    init_csv()
    logger.info(f"Soil sensor initialised at address {hex(config.SOIL_SENSOR_ADDR)}")
    logger.info(f"Logging locally to {CSV_PATH}")

    while True:
        try:
            moisture, temp = read_once(ss)

            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            print(f"{date_str} {time_str} | Moisture: {moisture}\tTemp: {temp:.1f}C")

            log_to_csv(date_str, time_str, moisture, temp)

            send(config.FEED_SOIL_MOISTURE, moisture)
            send(config.FEED_SOIL_TEMP, round(temp, 2))

        except Exception as e:
            logger.error(f"Soil sensor read failed: {e}")

        time.sleep(config.SOIL_INTERVAL_SEC)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_loop()
