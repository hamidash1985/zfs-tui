from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


CONFIG_DIR = Path.home() / ".config" / "zfs-tui"
CONFIG_FILE = CONFIG_DIR / "config.json"
HOSTS_FILE = CONFIG_DIR / "hosts.json"


@dataclass
class SshHostConfig:
    hostname: str
    port: int = 22
    username: str = ""
    identity_file: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class Config:
    sudo_keep_timeout: int = 300
    refresh_interval: float = 5.0
    color_theme: str = "default"
    default_pool_properties: list[str] = field(default_factory=lambda: [
        "name", "size", "allocated", "free", "fragmentation",
        "capacity", "dedupratio", "health", "altroot",
    ])
    default_dataset_properties: list[str] = field(default_factory=lambda: [
        "name", "used", "available", "referenced", "compressratio",
        "mountpoint", "quota", "compression", "atime",
    ])
    ssh_hosts: list[SshHostConfig] = field(default_factory=list)
    last_host: str = "localhost"


class ConfigManager:
    def __init__(self):
        self.config = Config()
        self._ensure_dirs()
        self.load()

    def _ensure_dirs(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                hosts_data = data.pop("ssh_hosts", [])
                self.config = Config(**data)
                self.config.ssh_hosts = [
                    SshHostConfig(**h) for h in hosts_data
                ]
            except (json.JSONDecodeError, TypeError) as e:
                pass

    def save(self):
        data = {
            "sudo_keep_timeout": self.config.sudo_keep_timeout,
            "refresh_interval": self.config.refresh_interval,
            "color_theme": self.config.color_theme,
            "last_host": self.config.last_host,
            "ssh_hosts": [
                {
                    "hostname": h.hostname,
                    "port": h.port,
                    "username": h.username,
                    "identity_file": h.identity_file,
                    "display_name": h.display_name,
                }
                for h in self.config.ssh_hosts
            ],
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    def add_ssh_host(self, host: SshHostConfig):
        existing = [h for h in self.config.ssh_hosts if h.hostname == host.hostname]
        if existing:
            self.config.ssh_hosts.remove(existing[0])
        self.config.ssh_hosts.append(host)
        self.save()

    def remove_ssh_host(self, hostname: str):
        self.config.ssh_hosts = [
            h for h in self.config.ssh_hosts if h.hostname != hostname
        ]
        self.save()
