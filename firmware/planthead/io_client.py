"""
Thin wrapper around the Adafruit IO REST client so every module
sends data the same way and errors are handled in one place.
"""
import logging
from Adafruit_IO import Client, RequestError

import config

logger = logging.getLogger("planthead.io_client")

_aio = None


def get_client():
    """Lazily create and reuse a single Adafruit IO client instance."""
    global _aio
    if _aio is None:
        if not config.AIO_USERNAME or not config.AIO_KEY:
            raise RuntimeError(
                "AIO_USERNAME / AIO_KEY not set — check your .env file"
            )
        _aio = Client(config.AIO_USERNAME, config.AIO_KEY)
    return _aio


def send(feed_key, value):
    """
    Send a single value to a feed. Returns True on success, False on failure.
    Never raises — callers should keep looping even if one upload fails
    (e.g. WiFi hiccup), rather than crashing the whole data-collection process.
    """
    try:
        aio = get_client()
        aio.send_data(feed_key, value)
        logger.info(f"Sent to {feed_key}: {str(value)[:60]}")
        return True
    except RequestError as e:
        logger.error(f"Adafruit IO rejected data for {feed_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send to {feed_key}: {e}")
        return False
