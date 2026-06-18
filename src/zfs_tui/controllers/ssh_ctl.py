from typing import Optional
from dataclasses import dataclass, field
import asyncio


class SshConnection:
    def __init__(self, hostname: str, port: int = 22,
                 username: str = "", identity_file: Optional[str] = None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.identity_file = identity_file
        self._process: Optional[asyncio.subprocess.Process] = None

    @property
    def _ssh_base(self) -> list[str]:
        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
            "-p", str(self.port),
        ]
        if self.identity_file:
            cmd.extend(["-i", self.identity_file])
        user_part = f"{self.username}@" if self.username else ""
        cmd.append(f"{user_part}{self.hostname}")
        return cmd

    async def run_command(self, cmd: list[str]) -> tuple[int, str, str]:
        full_cmd = self._ssh_base + cmd
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=60
            )
            return (
                proc.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            return (-1, "", "SSH command timed out")

    async def test_connection(self) -> tuple[bool, str]:
        ret, stdout, stderr = await self.run_command(["true"])
        if ret == 0:
            return True, "Connection successful"
        return False, stderr.strip()

    async def close(self):
        if self._process and self._process.returncode is None:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                pass
