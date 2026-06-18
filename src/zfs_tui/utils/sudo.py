from enum import Enum
from typing import Optional
import asyncio
import time


class SudoMode(Enum):
    DIRECT = "direct"
    SUDO = "sudo"
    DOAS = "doas"


class SudoContext:
    def __init__(self, timeout: int = 300):
        self.mode: SudoMode = SudoMode.SUDO
        self._sudo_available: Optional[bool] = None
        self._last_auth: float = 0
        self._timeout = timeout
        self._elevated = False

    @property
    def prefix(self) -> list[str]:
        if self.mode == SudoMode.DIRECT:
            return []
        return [self.mode.value]

    @property
    def is_elevated(self) -> bool:
        if self.mode == SudoMode.DIRECT:
            return True
        return (
            self._elevated
            and (time.monotonic() - self._last_auth) < self._timeout
        )

    async def check(self) -> bool:
        if self.mode == SudoMode.DIRECT:
            self._elevated = True
            return True
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-n", "true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ret = await proc.wait()
        if ret == 0:
            self._elevated = True
            self._last_auth = time.monotonic()
            return True
        return False

    async def authenticate(self) -> bool:
        if self.mode == SudoMode.DIRECT:
            self._elevated = True
            return True
        proc = await asyncio.create_subprocess_exec(
            "sudo", "-v",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        ret = await proc.wait()
        if ret == 0:
            self._elevated = True
            self._last_auth = time.monotonic()
            return True
        return False

    def invalidate(self):
        self._elevated = False
        self._last_auth = 0

    async def run(
        self, cmd: list[str], input_data: Optional[bytes] = None,
        timeout: float = 60.0,
    ) -> tuple[int, str, str]:
        full_cmd = self.prefix + cmd
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_data else None,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_data), timeout=timeout
            )
            return (
                proc.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            return (-1, "", f"Command timed out after {timeout}s")
