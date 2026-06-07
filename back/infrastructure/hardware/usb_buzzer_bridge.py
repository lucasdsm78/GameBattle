from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
import time
from pathlib import Path
from typing import Any, Optional

import httpx


@dataclass(slots=True)
class HidDeviceBinding:
    team: str
    label: str
    vendor_id: int
    product_id: int
    path: str = ""
    match_hex: str = ""
    match_byte_index: int = 0
    match_byte_value: int = 1
    debounce_ms: int = 500

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HidDeviceBinding":
        return cls(
            team=str(payload.get("team", "")).strip(),
            label=str(payload.get("label", "USB Buzzer")).strip() or "USB Buzzer",
            vendor_id=_parse_int(payload.get("vendor_id", 0)),
            product_id=_parse_int(payload.get("product_id", 0)),
            path=str(payload.get("path", "")).strip(),
            match_hex=str(payload.get("match_hex", "")).strip().lower(),
            match_byte_index=max(_parse_int(payload.get("match_byte_index", 0)), 0),
            match_byte_value=max(_parse_int(payload.get("match_byte_value", 1)), 0),
            debounce_ms=max(_parse_int(payload.get("debounce_ms", 500)), 0),
        )

    def validate(self) -> None:
        if not self.team:
            raise ValueError("Chaque binding matériel doit cibler une équipe.")
        if self.vendor_id <= 0 or self.product_id <= 0:
            raise ValueError(f"Binding invalide pour {self.label}: vendor_id/product_id requis.")

    def matches(self, report: list[int]) -> bool:
        if self.match_hex:
            hex_report = "".join(f"{byte:02x}" for byte in report)
            return hex_report.startswith(self.match_hex)
        if self.match_byte_index >= len(report):
            return False
        return report[self.match_byte_index] == self.match_byte_value


@dataclass(slots=True)
class BridgeTarget:
    api_base_url: str
    hardware_token: str

    @property
    def buzzer_event_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/api/hardware/buzzer-events"


@dataclass(slots=True)
class UsbBuzzerBridgeConfig:
    poll_interval_ms: int
    request_timeout_seconds: float
    bindings: list[HidDeviceBinding]

    @classmethod
    def from_file(cls, file_path: Path) -> "UsbBuzzerBridgeConfig":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        bindings = [HidDeviceBinding.from_dict(item) for item in payload.get("bindings", [])]
        if not bindings:
            raise ValueError("Le fichier de configuration des buzzers USB ne contient aucun binding.")
        for binding in bindings:
            binding.validate()
        return cls(
            poll_interval_ms=max(_parse_int(payload.get("poll_interval_ms", 30)), 5),
            request_timeout_seconds=max(float(payload.get("request_timeout_seconds", 5.0)), 0.5),
            bindings=bindings,
        )


class UsbBuzzerBridge:
    def __init__(self, target: BridgeTarget, config: UsbBuzzerBridgeConfig) -> None:
        self._target = target
        self._config = config
        self._last_triggered_at: dict[str, float] = {}

    async def run(self) -> None:
        await asyncio.gather(*(self._watch_binding(binding) for binding in self._config.bindings))

    async def _watch_binding(self, binding: HidDeviceBinding) -> None:
        while True:
            try:
                await self._watch_binding_session(binding)
            except Exception as exc:
                print(f"[usb-buzzer] {binding.label}: {exc}")
                await asyncio.sleep(2.0)

    async def _watch_binding_session(self, binding: HidDeviceBinding) -> None:
        hid = _import_hid_module()
        device = hid.device()
        if binding.path:
            device.open_path(binding.path.encode())
        else:
            device.open(binding.vendor_id, binding.product_id)
        device.set_nonblocking(True)
        print(f"[usb-buzzer] connecté: {binding.label} -> {binding.team}")

        try:
            while True:
                report = device.read(64)
                if report and binding.matches(report) and self._can_emit(binding):
                    await self._emit_event(binding, report)
                await asyncio.sleep(self._config.poll_interval_ms / 1000)
        finally:
            device.close()

    def _can_emit(self, binding: HidDeviceBinding) -> bool:
        now = time.monotonic() * 1000
        last = self._last_triggered_at.get(binding.label, 0.0)
        if now - last < binding.debounce_ms:
            return False
        self._last_triggered_at[binding.label] = now
        return True

    async def _emit_event(self, binding: HidDeviceBinding, report: list[int]) -> None:
        headers = {"X-GameBattle-Hardware-Token": self._target.hardware_token}
        payload = {"team": binding.team}
        timeout = httpx.Timeout(self._config.request_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self._target.buzzer_event_url, json=payload, headers=headers)
            response.raise_for_status()
        print(f"[usb-buzzer] buzz envoyé: {binding.label} -> {binding.team} ({''.join(f'{byte:02x}' for byte in report)})")


def _parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped.startswith("0x"):
            return int(stripped, 16)
        return int(stripped or "0")
    return int(value or 0)


def _import_hid_module():
    try:
        import hid  # type: ignore
    except ImportError as exc:  # pragma: no cover - dépend de la machine locale
        raise RuntimeError(
            "Le module 'hid' est requis pour utiliser le bridge USB. Installez 'hidapi' dans la venv backend."
        ) from exc
    return hid


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge local pour buzzers USB GameBattle")
    parser.add_argument("--config", required=True, help="Chemin vers le fichier JSON de bindings HID")
    parser.add_argument("--api-base-url", required=True, help="Base URL du backend local, ex: http://127.0.0.1:8000")
    parser.add_argument("--hardware-token", required=True, help="Token matériel GAMEBATTLE_HARDWARE_TOKEN")
    return parser


async def _main_async() -> None:
    args = build_argument_parser().parse_args()
    config = UsbBuzzerBridgeConfig.from_file(Path(args.config).resolve())
    bridge = UsbBuzzerBridge(
        target=BridgeTarget(api_base_url=args.api_base_url, hardware_token=args.hardware_token),
        config=config,
    )
    await bridge.run()


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()

