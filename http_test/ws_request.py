"""
This module performs the websockets connection, sends a message and returns
a response, using asyncio, via the python-websockets library.
"""

import asyncio
import logging
import ssl

import certifi
import websockets
from websockets.exceptions import InvalidStatusCode

NO_RESPONSE = {
    "status_code": 0,
    "response_body": b"",
}

# CAUTION! Enabling DEBUG logging for websockets makes the requests fail.
# Failures are caused by exception objects being logged directly, and
# not as strings.
#
# logging.basicConfig(format="[%(asctime)s] %(message)s", level=logging.DEBUG)


def headers_to_dict(headers: list) -> dict:
    headers_dict = dict()
    for header, value in map(lambda h: h.split(":", 1), headers):
        headers_dict[header.strip().lower()] = value.strip()
    return headers_dict


def get_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
    ssl_context.load_verify_locations(certifi.where())

    return ssl_context


async def ws_connect(
    url,
    host=None,
    port=None,
    server_hostname=None,
    message="Hello",
    extra_headers=None,
    read_timeout=3,
):
    """
    Connect to a websocket URL and send a message.
    Returns any response received from the server.
    """
    try:
        ws_connect_args = {
            "host": host,
            "port": port,
            "compression": None,
            "close_timeout": read_timeout,
            "extra_headers": headers_to_dict(extra_headers),
        }

        is_secure_ws = url.startswith("wss://")
        if is_secure_ws:
            ws_connect_args.update(server_hostname=server_hostname, ssl=get_ssl_context())

        async with websockets.connect(url, **ws_connect_args) as websocket:
            try:
                logging.info(f"> {message}")
                await websocket.send(message)
                await asyncio.sleep(0)

                try:
                    response = await asyncio.wait_for(websocket.recv(), read_timeout)
                except asyncio.TimeoutError:
                    logging.warning("Timeout while waiting for websocket response")
                    return NO_RESPONSE

            except websockets.ConnectionClosed:
                logging.warning("Connection closed while waiting for websocket response")
                return NO_RESPONSE

            response = {
                # Is there an HTTP status for a websocket connection?
                "status_code": 200,
                "response_body": response.encode(),
            }

            logging.info(f"< {response}")
            return response

    except InvalidStatusCode as e:
        logging.warning(f"Invalid status code received: {e.status_code}")
        return {
            "status_code": e.status_code,
            "response_headers": e.headers,
            "exception": e,
        }
