from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from fieldos.airgap import AirgapController
from fieldos.auth import OperatorAuth
from fieldos.engine import OperationsEngine
from fieldos.maps import OfflineMapStore
from fieldos.operations import OperationSessionManager
from fieldos.profiles import PROFILES, ProfileManager
from fieldos.vault import Vault


def _active_operation() -> tuple[OperationSessionManager, str]:
    manager = OperationSessionManager()
    return manager, manager.active.id


def _vault_from_pin(auth: OperatorAuth) -> Vault:
    pin = getpass.getpass("Operator PIN: ")
    if not auth.verify_pin(pin):
        raise SystemExit("AUTH // DENIED")
    return Vault(auth.vault_key_from_pin(pin))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fieldos-control", description="FIELD//OS control plane")
    sub = parser.add_subparsers(dest="command", required=True)

    profile = sub.add_parser("profile")
    profile.add_argument("name", nargs="?")

    airgap = sub.add_parser("airgap")
    airgap.add_argument("state", choices=("status", "on", "off"))
    airgap.add_argument("--confirm", action="store_true")

    asset = sub.add_parser("asset")
    asset_sub = asset.add_subparsers(dest="asset_command", required=True)
    asset_add = asset_sub.add_parser("add")
    asset_add.add_argument("kind")
    asset_add.add_argument("value")
    asset_add.add_argument("--label", default="")
    asset_sub.add_parser("list")

    evidence = sub.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    ingest = evidence_sub.add_parser("ingest")
    ingest.add_argument("path")
    ingest.add_argument("--asset")
    ingest.add_argument("--encrypt", action="store_true")
    evidence_sub.add_parser("list")
    verify = evidence_sub.add_parser("verify")
    verify.add_argument("id")
    verify.add_argument("--encrypted", action="store_true")

    maps = sub.add_parser("maps")
    maps.add_argument("action", choices=("list",))

    wp = sub.add_parser("waypoint")
    wp_sub = wp.add_subparsers(dest="waypoint_command", required=True)
    wp_add = wp_sub.add_parser("add")
    wp_add.add_argument("latitude", type=float)
    wp_add.add_argument("longitude", type=float)
    wp_add.add_argument("label")
    wp_sub.add_parser("list")

    auth = sub.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    auth_sub.add_parser("status")
    auth_sub.add_parser("init-pin")
    auth_sub.add_parser("verify")
    auth_sub.add_parser("lock")
    key = auth_sub.add_parser("add-key")
    key.add_argument("path")

    sub.add_parser("timeline")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    profiles = ProfileManager()

    if args.command == "profile":
        if args.name:
            profile = profiles.set(args.name)
            print(f"PROFILE // {profile.name} // NETWORK {profile.network_policy} // HARDWARE {profile.hardware_policy}")
        else:
            print(f"PROFILE // {profiles.current.name}")
            print("AVAILABLE // " + " | ".join(profile.name for profile in PROFILES))
        return 0

    if args.command == "airgap":
        controller = AirgapController()
        status = controller.status() if args.state == "status" else (controller.enable(confirm=args.confirm) if args.state == "on" else controller.disable(confirm=args.confirm))
        print(f"AIRGAP // {'ACTIVE' if status.active else 'OFF'} // {status.detail}")
        return 0 if status.supported or args.state == "status" else 1

    manager, operation_id = _active_operation()
    engine = OperationsEngine()

    if args.command == "asset":
        if args.asset_command == "add":
            asset = engine.upsert_asset(operation_id, args.kind, args.value, label=args.label)
            print(f"ASSET // {asset.id} // {asset.kind} // {asset.value}")
        else:
            for item in engine.list_assets(operation_id):
                print(f"{item.id}  {item.kind:<12} {item.value:<24} {item.label}")
        return 0

    if args.command == "evidence":
        auth = OperatorAuth()
        if args.evidence_command == "ingest":
            vault = _vault_from_pin(auth) if args.encrypt else None
            item = engine.ingest_evidence(operation_id, Path(args.path), operation_path=manager.session_path(), asset_id=args.asset, vault=vault)
            print(f"EVIDENCE // {item.id} // SHA256 {item.sha256} // {'ENCRYPTED' if item.encrypted else 'PLAIN'}")
        elif args.evidence_command == "list":
            for item in engine.list_evidence(operation_id):
                print(f"{item.id}  {item.sha256[:12]}  {item.size:>10}  {'ENC' if item.encrypted else 'RAW'}  {item.source_name}")
        else:
            vault = _vault_from_pin(auth) if args.encrypted else None
            print(f"VERIFY // {args.id} // {'PASS' if engine.verify_evidence(args.id, vault=vault) else 'FAIL'}")
        return 0

    if args.command == "maps":
        store = OfflineMapStore()
        maps = store.maps()
        if not maps:
            print(f"MAPS // NONE // place .mbtiles files in {store.root}")
        for path in maps:
            print(f"MAP // {path.name}")
        return 0

    if args.command == "waypoint":
        store = OfflineMapStore()
        if args.waypoint_command == "add":
            item = store.add_waypoint(args.latitude, args.longitude, args.label, operation_id)
            engine.record_event(operation_id, "WAYPOINT", f"{item.id} {item.label}", metadata={"lat": item.latitude, "lon": item.longitude})
            print(f"WAYPOINT // {item.id} // {item.latitude:.6f},{item.longitude:.6f} // {item.label}")
        else:
            for item in store.waypoints():
                print(f"{item.id}  {item.latitude:.6f},{item.longitude:.6f}  {item.label}")
        return 0

    if args.command == "auth":
        auth = OperatorAuth()
        if args.auth_command == "status":
            status = auth.status()
            print(f"AUTH // {'CONFIGURED' if status.configured else 'DISABLED'} // {'LOCKED' if status.locked else 'UNLOCKED'} // KEY {'YES' if status.key_configured else 'NO'}")
        elif args.auth_command == "init-pin":
            first = getpass.getpass("New operator PIN: ")
            second = getpass.getpass("Confirm PIN: ")
            if first != second:
                raise SystemExit("AUTH // PIN MISMATCH")
            auth.configure_pin(first)
            print("AUTH // PIN CONFIGURED // LOCKED")
        elif args.auth_command == "verify":
            print("AUTH // " + ("OK" if auth.verify_pin(getpass.getpass("Operator PIN: ")) else "DENIED"))
        elif args.auth_command == "lock":
            auth.lock()
            print("AUTH // LOCKED")
        else:
            auth.configure_key(Path(args.path))
            print("AUTH // KEY CONFIGURED")
        return 0

    if args.command == "timeline":
        for event in reversed(engine.timeline(operation_id)):
            print(f"{event.timestamp}  {event.event_type:<10} {event.summary}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
