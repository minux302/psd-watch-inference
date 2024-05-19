from __future__ import annotations

import asyncio
import io
import json
import struct
import time
import uuid
from enum import Enum
from typing import NamedTuple, Optional
from urllib import request

from PIL import Image
from websockets import client as websockets_client
from websockets import exceptions as websockets_exceptions

from module.eventloop import AsyncApp
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
logger.setLevel(DEBUG)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)


class ClientEvent(Enum):
    progress = 0
    finished = 1
    interrupted = 2
    error = 3
    connected = 4
    disconnected = 5


class ClientMessage(NamedTuple):
    event: ClientEvent
    prompt_id: str = ""
    images: list[Image.Image] = []
    result: Optional[dict] = None
    error: Optional[str] = None
    queue_remaining: Optional[int] = 0


class Client:
    def __init__(self, ip="http://127.0.0.1", port="8188"):
        self.url = f"{ip}:{port}"
        self._id = str(uuid.uuid4())
        self._connected = False
        self._async_app = AsyncApp()

    def enqueue(self, workflow):
        if not self._connected:
            self._wait_connection()
        data = {"prompt": workflow, "client_id": self._id}
        data = json.dumps(data).encode("utf-8")
        req = request.Request(f"{self.url}/prompt", data)
        req = json.loads(request.urlopen(req).read())
        return req["prompt_id"]

    def _wait_connection(self, time_out=60):
        wait_time = 0
        self._connected = self.health_check()
        while not self._connected:
            self._connected = self.health_check()
            if wait_time > time_out:
                raise Exception("Connection timeout")
            else:
                print("waiting for connection with ComfyUI...")
                time.sleep(1)
                wait_time += 1

    def health_check(self):
        req = request.Request(f"{self.url}/system_stats")
        try:
            status = request.urlopen(req).status
            if status == 200:
                return True
            return False
        except Exception:
            return False

    async def _listen(self, prompt_id):
        url = self.url.replace("http", "ws", 1)
        async for websocket in websockets_client.connect(
            f"{url}/ws?clientId={self._id}",
            max_size=2**30,
            read_limit=2**30,
            ping_timeout=60,
        ):
            try:
                async for msg in self._listen_main(websocket, prompt_id):
                    yield msg
            except websockets_exceptions.ConnectionClosedError as e:
                logger.warning(f"Websocket connection closed: {str(e)}")
            except OSError as e:
                msg = "Could not connect to websocket server " + f"at {url}: {str(e)}"
            except asyncio.CancelledError:
                await websocket.close()
                break
            except Exception as e:
                logger.exception(f"Unhandled exception in websocket listener, {e}")

    async def _listen_main(
        self,
        websocket: websockets_client.WebSocketClientProtocol,
        prompt_id: str,
    ):
        images = []
        result = None

        async for msg in websocket:
            if isinstance(msg, bytes):
                image = _extract_message_png_image(memoryview(msg))
                if image is not None:
                    images.append(image)

            elif isinstance(msg, str):
                msg = json.loads(msg)
                if msg["type"] == "status":
                    yield ClientMessage(
                        event=ClientEvent.connected,
                        prompt_id=prompt_id,
                        queue_remaining=msg["data"]["status"]["exec_info"][
                            "queue_remaining"
                        ],
                    )

                # if msg["type"] == "progress":
                #     progress = msg["data"]["value"]
                #     yield ClientMessage(
                #         ClientEvent.progress, prompt_id, progress
                #     )

                if (
                    msg["type"] == "executing"
                    and msg["data"]["node"] is None
                    and msg["data"]["prompt_id"] == prompt_id
                ):
                    yield ClientMessage(
                        event=ClientEvent.finished, prompt_id=prompt_id, images=images
                    )

                if (
                    msg["type"] == "executed"
                    and msg["data"]["prompt_id"] == prompt_id
                    and images != []
                ):
                    yield ClientMessage(
                        event=ClientEvent.finished,
                        prompt_id=prompt_id,
                        images=images,
                        result=result,
                    )

    def polling(self, prompt_id) -> Image.Image:
        return self._async_app.run(self._polling(prompt_id))

    async def _polling(self, prompt_id) -> Image.Image | None:
        results = await self._receive_images(prompt_id)
        if isinstance(results, list) and isinstance(results[0], Image.Image):
            return results[0]
        else:
            return None

    async def _receive_images(self, prompt_id):
        async for msg in self._listen(prompt_id):
            if msg.event is ClientEvent.finished and msg.prompt_id == prompt_id:
                assert msg.images is not None
                return msg.images
            # if (
            #     msg.event is ClientEvent.connected
            #     and msg.prompt_id == prompt_id
            #     and msg.queue_remaining == 0
            # ):
            #     return
            # if (
            #     msg.event is ClientEvent.progress
            #     and msg.prompt_id == prompt_id
            # ):
            #     return msg.progress
            if msg.event is ClientEvent.error and msg.prompt_id == prompt_id:
                raise Exception(msg.error)
        assert False, "Connection closed without receiving images"


def _extract_message_png_image(data: memoryview) -> Optional[Image.Image]:
    s = struct.calcsize(">II")
    if len(data) > s:
        byte_data = data[s:].tobytes()
        byte_stream = io.BytesIO(byte_data)
        image = Image.open(byte_stream)
        return image
    return None
