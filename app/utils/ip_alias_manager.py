from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import List


@dataclass
class AliasApplyResult:
    requested_ips: List[str] = field(default_factory=list)
    existing_ips: List[str] = field(default_factory=list)
    created_ips: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class AliasRemoveResult:
    requested_ips: List[str] = field(default_factory=list)
    removed_ips: List[str] = field(default_factory=list)
    missing_ips: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class IPv4AddressInfo:
    ip: str
    prefix_origin: str
    address_state: str


class IPAliasManager:
    @staticmethod
    def _run_powershell(command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def list_adapters() -> List[str]:
        cmd = "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -ExpandProperty Name"
        proc = IPAliasManager._run_powershell(cmd)
        if proc.returncode != 0:
            return []
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    @staticmethod
    def list_ipv4_addresses(interface_alias: str) -> List[str]:
        alias = interface_alias.replace("'", "''")
        cmd = (
            f"Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '{alias}' "
            "| Select-Object -ExpandProperty IPAddress"
        )
        proc = IPAliasManager._run_powershell(cmd)
        if proc.returncode != 0:
            return []
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    @staticmethod
    def list_ipv4_info(interface_alias: str) -> List[IPv4AddressInfo]:
        alias = interface_alias.replace("'", "''")
        cmd = (
            f"Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '{alias}' "
            "| Select-Object IPAddress,PrefixOrigin,AddressState | ConvertTo-Json -Depth 4"
        )
        proc = IPAliasManager._run_powershell(cmd)
        if proc.returncode != 0:
            return []

        text = (proc.stdout or "").strip()
        if not text:
            return []

        try:
            parsed = json.loads(text)
        except Exception:
            return []

        rows = parsed if isinstance(parsed, list) else [parsed]
        out: List[IPv4AddressInfo] = []
        for row in rows:
            try:
                out.append(
                    IPv4AddressInfo(
                        ip=str(row.get("IPAddress", "")).strip(),
                        prefix_origin=str(row.get("PrefixOrigin", "")).strip(),
                        address_state=str(row.get("AddressState", "")).strip(),
                    )
                )
            except Exception:
                continue
        return [item for item in out if item.ip]

    @staticmethod
    def has_non_manual_ipv4(interface_alias: str) -> bool:
        infos = IPAliasManager.list_ipv4_info(interface_alias)
        for info in infos:
            origin = (info.prefix_origin or "").lower()
            if origin != "manual":
                return True
        return False

    @staticmethod
    def preferred_ipv4(interface_alias: str) -> str:
        """
        Pick a stable bind candidate for an adapter.
        Preference:
        1) Preferred + non-manual + non-link-local
        2) Preferred + non-link-local
        3) Any non-link-local
        4) First available IPv4
        """
        infos = IPAliasManager.list_ipv4_info(interface_alias)
        if not infos:
            return ""

        def is_preferred(item: IPv4AddressInfo) -> bool:
            return (item.address_state or "").strip().lower() == "preferred"

        def is_manual(item: IPv4AddressInfo) -> bool:
            return (item.prefix_origin or "").strip().lower() == "manual"

        def is_link_local(item: IPv4AddressInfo) -> bool:
            return (item.ip or "").startswith("169.254.")

        buckets = [
            [row for row in infos if is_preferred(row) and (not is_manual(row)) and (not is_link_local(row))],
            [row for row in infos if is_preferred(row) and (not is_link_local(row))],
            [row for row in infos if not is_link_local(row)],
            list(infos),
        ]
        for bucket in buckets:
            if bucket:
                return bucket[0].ip
        return ""

    @staticmethod
    def ensure_ip_aliases(interface_alias: str, ips: List[str], prefix_length: int = 24) -> AliasApplyResult:
        result = AliasApplyResult(requested_ips=list(ips))
        existing = set(IPAliasManager.list_ipv4_addresses(interface_alias))
        result.existing_ips = sorted(existing)

        alias = interface_alias.replace("'", "''")
        for ip in ips:
            if ip in existing:
                continue
            cmd = (
                f"New-NetIPAddress -InterfaceAlias '{alias}' -IPAddress '{ip}' "
                f"-PrefixLength {int(prefix_length)} -AddressFamily IPv4 -ErrorAction Stop"
            )
            proc = IPAliasManager._run_powershell(cmd)
            if proc.returncode == 0:
                result.created_ips.append(ip)
                existing.add(ip)
            else:
                err = (proc.stderr or proc.stdout or "unknown error").strip()
                result.errors.append(f"{ip}: {err}")

        return result

    @staticmethod
    def remove_ip_aliases(interface_alias: str, ips: List[str]) -> AliasRemoveResult:
        result = AliasRemoveResult(requested_ips=list(ips))
        existing = set(IPAliasManager.list_ipv4_addresses(interface_alias))
        alias = interface_alias.replace("'", "''")

        for ip in ips:
            if ip not in existing:
                result.missing_ips.append(ip)
                continue
            cmd = (
                f"Remove-NetIPAddress -InterfaceAlias '{alias}' -IPAddress '{ip}' "
                "-Confirm:$false -AddressFamily IPv4 -ErrorAction Stop"
            )
            proc = IPAliasManager._run_powershell(cmd)
            if proc.returncode == 0:
                result.removed_ips.append(ip)
                existing.discard(ip)
            else:
                err = (proc.stderr or proc.stdout or "unknown error").strip()
                result.errors.append(f"{ip}: {err}")

        return result

