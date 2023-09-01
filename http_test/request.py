import asyncio
import logging
import random
import string
import time
import zlib
from io import BytesIO, StringIO
from urllib.parse import urlparse

import brotli
import certifi
import pycurl

from http_test.ws_request import ws_connect


class Request:
    """
    Each `Request` instance represents a single test request to be performed.
    The `fire()` method performs the request and returns a dict structure with
    the results.
    """

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: list = None,
        connect_to: list = None,
        http2: bool = False,
        payload: str = None,
        verbose: bool = False,
    ):
        self.url = url
        self.method = method
        self.headers = headers if headers else []
        self.connect_to = connect_to
        self.http2 = http2
        self.verbose = verbose
        self.payload: str = payload if payload else None

        self.request_id = self.get_unique_request_identifier()

        # Define a custom user-agent string per request.
        # This will help us find the request in Datadog if needed.
        self.user_agent = f"User-Agent: {self.request_id}"
        self.headers.append(self.user_agent)

        self.response_headers = dict()

    def get_unique_request_identifier(self):
        ts = int(time.time())
        random_str = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        return f"HTTPTEST/{ts}.{random_str}"

    def client(self):
        c = pycurl.Curl()

        if self.method != "GET":
            c.setopt(c.CUSTOMREQUEST, self.method)

        c.setopt(c.URL, self.url)

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
        """
        Attempts to transparently decompress the response body if needed.
        """
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
        """
        Performs the HTTP/Websocket request and returns a dict structure with
        the results. The contents of the dictionary can vary based on the type
        of request being performed, and whether the request is done via pycurl
        or websocket-client.

        The following keys should generally be present:
        - `status_code`
        - `response_body`
        - `response_body_decoded`
        - `response_headers`
        """
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

        if self.payload:
            request_body = StringIO(self.payload)
            c.setopt(c.POST, 1)
            c.setopt(c.READDATA, request_body)
            c.setopt(c.POSTFIELDSIZE, len(self.payload))

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

    def resolve_connect_to(self):
        """
        Emulate curl's --connect-to functionality with the same semantics.
        Given the `self.connect_to` list of string entries, try to find a match
        to the current target url. If one is found, return the alternative host
        and port to connect to.

        This is probably trickier than I think it is, but the basics work.
        """
        parsed_url = urlparse(self.url)
        host = parsed_url.hostname
        port = (
            parsed_url.port
            if parsed_url.port
            else (443 if parsed_url.scheme == "https" or parsed_url.scheme == "wss" else 80)
        )

        if not self.connect_to:
            return host, port

        ct_host = host
        ct_port = port

        for connect_to_entry in self.connect_to:
            matching_entry = f"{host}:{port}:"
            if connect_to_entry.startswith(matching_entry):
                ct_host_port = connect_to_entry.split(":", 2)[2]
                if ":" in ct_host_port:
                    ct_host, ct_port = ct_host_port.split(":", 1)
                else:
                    ct_host = ct_host_port
                break

        # Could this be needed?
        # if ct_host != host and not self.header_in_list("host"):
        #    logging.info(f"Adding Host header: {host} to request")
        #    self.headers.append(f"Host: {host}")

        logging.warning(f"Connecting to host: {host}, port: {port} instead of {self.url}")

        return ct_host, int(ct_port)

    def header_in_list(self, header_name: str) -> bool:
        """
        Returns True if the given header name is present in the list of headers
        for this request.
        """
        for header in self.headers:
            if header_name.lower() + ":" in header.lower():
                return True

        return False

    def fire_websockets_request(self) -> dict:
        hostname = urlparse(self.url).hostname
        ct_host, ct_port = self.resolve_connect_to()
        result_dict = asyncio.run(
            ws_connect(
                self.url,
                host=ct_host,
                port=ct_port,
                server_hostname=hostname,
                message=self.payload,
                extra_headers=self.headers,
            )
        )

        result_dict["connect_to"] = self.connect_to
        result_dict["request_id"] = self.request_id

        return result_dict
