import base64
import json
import logging
import os
import random
import string
import time
import zlib
from io import BytesIO
from urllib.parse import urlparse

import brotli
import certifi
import pycurl
import yaml


class Request:
    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: list = None,
        connect_to: str = None,
        http2: bool = False,
        payload: str | bytes = None,
        verbose: bool = False,
    ):
        self.url = url
        self.method = method
        self.headers = headers if headers else []
        self.connect_to = connect_to
        self.http2 = http2
        self.verbose = verbose
        self.payload = payload

        self.request_id = self.get_unique_request_identifier()

        self.response_headers = dict()

    def get_unique_request_identifier(self):
        ts = int(time.time())
        random_str = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(4)
        )
        return f"HTTPTEST/{ts}.{random_str}"

    def client(self):
        c = pycurl.Curl()

        if self.method != "GET":
            c.setopt(c.CUSTOMREQUEST, self.method)

        c.setopt(c.URL, self.url)

        # Define a custom user-agent string per request.
        # This will help us find the request in Datadog if needed.
        self.user_agent = f"User-Agent: {self.request_id}"
        self.headers.append(self.user_agent)

        c.setopt(c.HTTPHEADER, self.headers)

        if self.connect_to:
            # print("Setting --connect-to to:", self.connect_to)
            c.setopt(c.CONNECT_TO, self.connect_to)

        c.setopt(c.CAINFO, certifi.where())

        if self.verbose:
            c.setopt(c.VERBOSE, True)

        if self.http2:
            c.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_2_0)
        else:
            c.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1)

        #
        # pycurl doesn't seem to inflate the response by itself based on encoding
        #
        ##for h in self.headers:
        ##    if "content-encoding" in h.lower():
        ##        c.setopt(c.ENCODING, h.split(":")[1].strip())

        return c

    def header_function(self, header_line):
        """
        From pycurl's documentation:
        http://pycurl.io/docs/latest/quickstart.html#examining-response-headers
        """
        # HTTP standard specifies that headers are encoded in iso-8859-1.
        # On Python 2, decoding step can be skipped.
        # On Python 3, decoding step is required.
        header_line = header_line.decode("iso-8859-1")

        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ":" not in header_line:
            return

        # Break the header line into header name and value.
        name, value = header_line.split(":", 1)

        # Remove whitespace that may be present.
        # Header lines include the trailing newline, and there may be whitespace
        # around the colon.
        name = name.strip()
        value = value.strip()

        # Header names are case insensitive.
        # Lowercase name here.
        name = name.lower()

        # Now we can actually record the header name and value.
        if name in self.response_headers:
            if isinstance(self.response_headers[name], list):
                self.response_headers[name].append(value)
            else:
                self.response_headers[name] = [self.response_headers[name], value]
        else:
            self.response_headers[name] = value

    def inflate_response(self, response_body: bytes) -> bytes:
        try:
            is_gzip = response_body[0] == 0x1F and response_body[1] == 0x8B
        except IndexError:
            # IndexError here indicates the response body was empty
            return response_body

        if is_gzip:
            return zlib.decompress(response_body, 16 + zlib.MAX_WBITS)

        try:
            return brotli.decompress(response_body)
        except brotli.error as e:
            logging.info("Error while trying to decompress brotli response", e)

        return response_body

    def is_websockets_request(self):
        scheme = urlparse(self.url).scheme
        return scheme in ("ws", "wss")

    def fire(self) -> dict:
        if self.is_websockets_request():
            result_dict = self.fire_websockets_request()
        else:
            result_dict = self.fire_pycurl_request()

        if "response_body" in result_dict:
            decoded_content = self.inflate_response(result_dict["response_body"])
            result_dict["response_body_decoded"] = decoded_content

        return result_dict

    def fire_pycurl_request(self) -> dict:
        response = BytesIO()

        c = self.client()
        c.setopt(c.WRITEDATA, response)

        self.response_headers.clear()
        c.setopt(c.HEADERFUNCTION, self.header_function)

        c.perform()

        result_dict = {
            "status_code": c.getinfo(c.RESPONSE_CODE),
            "connect_to": self.connect_to,
            "request_id": self.request_id,
            "request_headers": self.headers,
            "response_headers": self.response_headers,
            "response_body": response.getvalue(),
            "elapsed": c.getinfo(c.TOTAL_TIME),
        }

        c.close()

        return result_dict

    def fire_websockets_request(self) -> dict:
        from ws_request import ws_connect

        result_dict = ws_connect(
            self.url, message=self.payload, extra_headers=self.headers
        )

        return result_dict
