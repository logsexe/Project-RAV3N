from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from fieldos.engine import OperationsEngine


@dataclass(slots=True, frozen=True)
class ImportResult:
    adapter: str
    assets: int = 0
    events: int = 0
    evidence: int = 0


class IntegrationHub:
    """Parse structured tool output into FIELD//OS assets and timeline events.

    Adapters only ingest operator-supplied output files; they do not execute tools.
    """

    def __init__(self, engine: OperationsEngine) -> None:
        self.engine = engine

    def import_file(self, operation_id: str, adapter: str, path: Path) -> ImportResult:
        adapter = adapter.lower().strip()
        path = path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        handlers = {
            "nmap": self._import_nmap,
            "yara": self._import_yara,
            "zeek": self._import_zeek,
            "meshtastic": self._import_meshtastic,
            "gnss": self._import_gnss,
            "osint-json": self._import_osint_json,
        }
        if adapter not in handlers:
            raise ValueError(f"Unsupported adapter: {adapter}")
        result = handlers[adapter](operation_id, path)
        self.engine.record_event(
            operation_id,
            "IMPORT",
            f"{adapter} import {path.name}",
            metadata={"adapter": adapter, "path": str(path), "assets": result.assets, "events": result.events},
        )
        return result

    def _import_nmap(self, operation_id: str, path: Path) -> ImportResult:
        root = ET.parse(path).getroot()
        assets = events = 0
        for host in root.findall("host"):
            status = host.find("status")
            if status is not None and status.attrib.get("state") != "up":
                continue
            addresses = {a.attrib.get("addrtype", "address"): a.attrib.get("addr", "") for a in host.findall("address")}
            ip = addresses.get("ipv4") or addresses.get("ipv6")
            if not ip:
                continue
            hostname_node = host.find("hostnames/hostname")
            hostname = hostname_node.attrib.get("name", "") if hostname_node is not None else ""
            asset = self.engine.upsert_asset(operation_id, "IP", ip, label=hostname or ip, metadata={"source": "nmap", "hostname": hostname, "mac": addresses.get("mac", "")})
            assets += 1
            for port in host.findall("ports/port"):
                state = port.find("state")
                if state is None or state.attrib.get("state") != "open":
                    continue
                svc = port.find("service")
                portid = port.attrib.get("portid", "?")
                proto = port.attrib.get("protocol", "tcp")
                service = svc.attrib.get("name", "unknown") if svc is not None else "unknown"
                metadata = {"source": "nmap", "port": portid, "protocol": proto, "service": service}
                if svc is not None:
                    for key in ("product", "version", "extrainfo", "tunnel"):
                        if svc.attrib.get(key):
                            metadata[key] = svc.attrib[key]
                self.engine.record_event(operation_id, "SERVICE", f"{ip}:{portid}/{proto} {service}", asset_id=asset.id, metadata=metadata)
                events += 1
        return ImportResult("nmap", assets, events)

    def _import_yara(self, operation_id: str, path: Path) -> ImportResult:
        events = 0
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            rule = parts[0]
            target = parts[1] if len(parts) > 1 else "unknown"
            self.engine.record_event(operation_id, "YARA", f"{rule} -> {target}", metadata={"source": "yara", "rule": rule, "target": target})
            events += 1
        return ImportResult("yara", 0, events)

    def _import_zeek(self, operation_id: str, path: Path) -> ImportResult:
        fields: list[str] = []
        assets_seen: set[tuple[str, str]] = set()
        events = 0
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.startswith("#fields"):
                fields = raw.split("\t")[1:]
                continue
            if not raw or raw.startswith("#") or not fields:
                continue
            values = raw.split("\t")
            row = dict(zip(fields, values))
            src = row.get("id.orig_h", "")
            dst = row.get("id.resp_h", "")
            for value in (src, dst):
                if value and value != "-" and ("IP", value) not in assets_seen:
                    self.engine.upsert_asset(operation_id, "IP", value, metadata={"source": "zeek"})
                    assets_seen.add(("IP", value))
            summary = f"{src}:{row.get('id.orig_p','?')} -> {dst}:{row.get('id.resp_p','?')} {row.get('service','-')}"
            self.engine.record_event(operation_id, "ZEEK", summary, metadata={"source": "zeek", **{k: v for k, v in row.items() if k in {"proto", "service", "duration", "conn_state"}}})
            events += 1
        return ImportResult("zeek", len(assets_seen), events)

    def _import_meshtastic(self, operation_id: str, path: Path) -> ImportResult:
        payload = json.loads(path.read_text(encoding="utf-8"))
        nodes = payload.get("nodes", payload) if isinstance(payload, dict) else payload
        if isinstance(nodes, dict):
            nodes = list(nodes.values())
        assets = events = 0
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            user = node.get("user", {}) if isinstance(node.get("user", {}), dict) else {}
            node_id = str(user.get("id") or node.get("id") or node.get("num") or "").strip()
            if not node_id:
                continue
            label = str(user.get("longName") or user.get("shortName") or node_id)
            asset = self.engine.upsert_asset(operation_id, "MESH_NODE", node_id, label=label, metadata={"source": "meshtastic", "user": user})
            assets += 1
            position = node.get("position") if isinstance(node.get("position"), dict) else {}
            if position:
                self.engine.record_event(operation_id, "MESH", f"{label} position update", asset_id=asset.id, metadata={"source": "meshtastic", "position": position})
                events += 1
        return ImportResult("meshtastic", assets, events)

    def _import_gnss(self, operation_id: str, path: Path) -> ImportResult:
        events = 0
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if item.get("class") != "TPV" or "lat" not in item or "lon" not in item:
                continue
            metadata = {k: item[k] for k in ("lat", "lon", "alt", "speed", "track", "time", "mode") if k in item}
            self.engine.record_event(operation_id, "GNSS", f"fix {item['lat']:.6f},{item['lon']:.6f}", metadata=metadata)
            events += 1
        return ImportResult("gnss", 0, events)

    def _import_osint_json(self, operation_id: str, path: Path) -> ImportResult:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("results", payload.get("records", [])) if isinstance(payload, dict) else []
        assets = events = 0
        kind_map = {"ip": "IP", "domain": "DOMAIN", "hostname": "HOSTNAME", "email": "EMAIL", "url": "URL"}
        for record in records if isinstance(records, list) else []:
            if not isinstance(record, dict):
                continue
            for key, kind in kind_map.items():
                value = record.get(key)
                if isinstance(value, str) and value.strip():
                    asset = self.engine.upsert_asset(operation_id, kind, value.strip(), metadata={"source": "osint-json", "record": record})
                    assets += 1
                    self.engine.record_event(operation_id, "OSINT", f"{kind} enrichment {value.strip()}", asset_id=asset.id, metadata={"source": "osint-json"})
                    events += 1
        return ImportResult("osint-json", assets, events)
