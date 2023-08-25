import asyncio
import json
import ssl

import certifi
import websockets


async def wss_handshake(url):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
    ssl_context.load_verify_locations(certifi.where())

    async with websockets.connect(
        url, extra_headers={"Origin": "kahoot-experimental.it"}, ssl=ssl_context
    ) as websocket:
        await websocket.send(
            json.dumps(
                {"channel": "/meta/handshake", "version": "1.0", "supportedConnectionTypes": ["websocket"], "id": "1"},
                indent=4,
                sort_keys=True,
            )
        )

        response = await websocket.recv()
        print(f"< {response}")

        return response


uri = "wss://play.kahoot-experimental.it/cometd/71/4a7be79255384e8527d7e3ada6550602d03deb98298c5bcf3dece3b4f9e7246a"
asyncio.get_event_loop().run_until_complete(wss_handshake(uri))
