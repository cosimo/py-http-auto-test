"""
This module performs the websockets connection, sends a message and returns
a response, without having to do any asyncio shenanigans.
"""

import logging

from websocket import create_connection
from websocket._exceptions import WebSocketBadStatusException


def select_origin_header(extra_headers):
    origin = None
    headers_no_origin = []

    for header in extra_headers:
        if header.lower().startswith("origin:"):
            origin = header.lower().replace("origin: ", "")
        else:
            headers_no_origin.append(header)
    return origin, headers_no_origin


def ws_connect(ws_url, message="Hello", extra_headers=None):
    """
    Connect to a websocket URL and send a message.
    Returns any response received from the server.
    """
    # Needed to avoid sending an extra Origin HTTP header,
    # which is currently crashing our cors lua code
    origin, extra_headers = select_origin_header(extra_headers)

    try:
        ws = create_connection(ws_url, timeout=3, header=extra_headers)
        # print("<<<", ws.recv())
        # print(f"Sending message '{message}'")
        ws.send(message)
        result = {
            "status_code": 200,
            "response_body": ws.recv().encode(),
        }
        # print(f"<<< Received '{result}'")
        ws.close()

    except WebSocketBadStatusException as e:
        logging.error(
            f"Error while trying to connect to websocket: status_code={e.status_code}"
            f" resp_headers={e.resp_headers} resp_body={e.resp_body}"
        )
        result = {
            "status_code": e.status_code,
            "response_body": e.resp_body,
            "response_headers": e.resp_headers,
        }

    return result
