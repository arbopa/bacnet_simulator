from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.models.project_model import ProjectModel

from .bacnet_device import BacnetDeviceServer

logger = logging.getLogger(__name__)


class BacnetManager(QObject):
    status_changed = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: Optional[ProjectModel] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tick_event: Optional[asyncio.Event] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._server: Optional[BacnetDeviceServer] = None
        self._running = False
        self._available = self._check_bacpypes3()

    @staticmethod
    def _check_bacpypes3() -> bool:
        try:
            import bacpypes3  # noqa: F401

            return True
        except Exception:
            return False

    @staticmethod
    def _patch_bacpypes3_ipv4_reuse_port() -> None:
        """
        BACpypes3 currently requests reuse_port=True in IPv4 endpoint creation.
        On Windows/Python this may raise ValueError("reuse_port not supported").
        Apply a runtime patch that transparently falls back to no reuse_port.
        """
        try:
            import bacpypes3.ipv4 as b3_ipv4
        except Exception:
            return

        cls = getattr(b3_ipv4, "IPv4DatagramServer", None)
        proto_cls = getattr(b3_ipv4, "IPv4DatagramProtocol", None)
        retry_interval = float(getattr(b3_ipv4, "BACPYPES_ENDPOINT_RETRY_INTERVAL", 1.0))
        if cls is None or proto_cls is None:
            return
        if getattr(cls, "_codex_reuse_port_patch", False):
            return

        async def patched_retrying_create_datagram_endpoint(self, loop, addrTuple, bind_socket=None):
            while True:
                try:
                    if bind_socket:
                        return await loop.create_datagram_endpoint(proto_cls, sock=bind_socket)

                    try:
                        return await loop.create_datagram_endpoint(
                            proto_cls,
                            local_addr=addrTuple,
                            allow_broadcast=True,
                            reuse_port=True,
                        )
                    except ValueError as err:
                        if "reuse_port" not in str(err):
                            raise
                        return await loop.create_datagram_endpoint(
                            proto_cls,
                            local_addr=addrTuple,
                            allow_broadcast=True,
                        )
                except OSError:
                    await asyncio.sleep(retry_interval)

        cls.retrying_create_datagram_endpoint = patched_retrying_create_datagram_endpoint
        cls._codex_reuse_port_patch = True
        logger.info("Applied BACpypes3 IPv4 reuse_port compatibility patch.")

    @property
    def available(self) -> bool:
        return self._available

    def set_project(self, project: ProjectModel) -> None:
        self._project = project

    def start(self) -> None:
        if self._running:
            return
        if self._project is None:
            self.error.emit("Cannot start BACnet: no project loaded.")
            return
        if not self._available:
            self.error.emit("BACpypes3 not available in the current Python environment.")
            return

        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        loop = self._loop
        stop_event = self._stop_event
        if loop and stop_event and (not loop.is_closed()):
            loop.call_soon_threadsafe(stop_event.set)
        self._running = False
        self.status_changed.emit("BACnet stopping")

    def notify_simulation_tick(self) -> None:
        if not self._running:
            return
        loop = self._loop
        tick_event = self._tick_event
        if (loop is None) or (tick_event is None) or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(tick_event.set)
        except RuntimeError:
            self._running = False

    def _thread_main(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._tick_event = asyncio.Event()
        self._stop_event = asyncio.Event()

        async def runner():
            assert self._project is not None
            self._patch_bacpypes3_ipv4_reuse_port()
            bind_ip = self._project.bacnet.bind_ip
            self._server = BacnetDeviceServer(bind_ip)
            try:
                await self._server.start(self._project.devices)
                self._running = True
                self.status_changed.emit("BACnet running")
                await self._server.loop_forever(self._tick_event, self._stop_event)
            except Exception as err:
                logger.exception("BACnet manager failed")
                self.error.emit(f"BACnet start failed: {err}")
            finally:
                try:
                    if self._server:
                        await self._server.stop()
                finally:
                    self._running = False
                    self.status_changed.emit("BACnet stopped")

        try:
            self._loop.run_until_complete(runner())
        finally:
            self._loop.close()
            self._loop = None
            self._tick_event = None
            self._stop_event = None
            self._server = None
