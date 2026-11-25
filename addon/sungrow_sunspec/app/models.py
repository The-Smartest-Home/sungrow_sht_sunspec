"""SunSpec model layouts and Sungrow source-register mapping validation."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("sungrow_sunspec.models")

# Point name, register width, SunSpec scalar type, associated scale factor.
INVERTER_POINTS = (
    ("A", 1, "uint16", "A_SF"),
    ("AphA", 1, "uint16", "A_SF"),
    ("AphB", 1, "uint16", "A_SF"),
    ("AphC", 1, "uint16", "A_SF"),
    ("A_SF", 1, "sunssf", None),
    ("PPVphAB", 1, "uint16", "V_SF"),
    ("PPVphBC", 1, "uint16", "V_SF"),
    ("PPVphCA", 1, "uint16", "V_SF"),
    ("PhVphA", 1, "uint16", "V_SF"),
    ("PhVphB", 1, "uint16", "V_SF"),
    ("PhVphC", 1, "uint16", "V_SF"),
    ("V_SF", 1, "sunssf", None),
    ("W", 1, "int16", "W_SF"),
    ("W_SF", 1, "sunssf", None),
    ("Hz", 1, "uint16", "Hz_SF"),
    ("Hz_SF", 1, "sunssf", None),
    ("VA", 1, "int16", "VA_SF"),
    ("VA_SF", 1, "sunssf", None),
    ("VAr", 1, "int16", "VAr_SF"),
    ("VAr_SF", 1, "sunssf", None),
    ("PF", 1, "int16", "PF_SF"),
    ("PF_SF", 1, "sunssf", None),
    ("WH", 2, "acc32", "WH_SF"),
    ("WH_SF", 1, "sunssf", None),
    ("DCA", 1, "uint16", "DCA_SF"),
    ("DCA_SF", 1, "sunssf", None),
    ("DCV", 1, "uint16", "DCV_SF"),
    ("DCV_SF", 1, "sunssf", None),
    ("DCW", 1, "int16", "DCW_SF"),
    ("DCW_SF", 1, "sunssf", None),
    ("TmpCab", 1, "int16", "Tmp_SF"),
    ("TmpSnk", 1, "int16", "Tmp_SF"),
    ("TmpTrns", 1, "int16", "Tmp_SF"),
    ("TmpOt", 1, "int16", "Tmp_SF"),
    ("Tmp_SF", 1, "sunssf", None),
    ("St", 1, "enum16", None),
    ("StVnd", 1, "enum16", None),
    ("Evt1", 2, "bitfield32", None),
    ("Evt2", 2, "bitfield32", None),
    ("EvtVnd1", 2, "bitfield32", None),
    ("EvtVnd2", 2, "bitfield32", None),
    ("EvtVnd3", 2, "bitfield32", None),
    ("EvtVnd4", 2, "bitfield32", None),
)

STORAGE_POINTS = (
    ("WChaMax", 1, "uint16", "WChaMax_SF"),
    ("WChaGra", 1, "uint16", "WChaDisChaGra_SF"),
    ("WDisChaGra", 1, "uint16", "WChaDisChaGra_SF"),
    ("StorCtl_Mod", 1, "bitfield16", None),
    ("VAChaMax", 1, "uint16", "VAChaMax_SF"),
    ("MinRsvPct", 1, "uint16", "MinRsvPct_SF"),
    ("ChaState", 1, "uint16", "ChaState_SF"),
    ("StorAval", 1, "uint16", "StorAval_SF"),
    ("InBatV", 1, "uint16", "InBatV_SF"),
    ("ChaSt", 1, "enum16", None),
    ("OutWRte", 1, "int16", "InOutWRte_SF"),
    ("InWRte", 1, "int16", "InOutWRte_SF"),
    ("InOutWRte_WinTms", 1, "uint16", None),
    ("InOutWRte_RvrtTms", 1, "uint16", None),
    ("InOutWRte_RmpTms", 1, "uint16", None),
    ("ChaGriSet", 1, "enum16", None),
    ("WChaMax_SF", 1, "sunssf", None),
    ("WChaDisChaGra_SF", 1, "sunssf", None),
    ("VAChaMax_SF", 1, "sunssf", None),
    ("MinRsvPct_SF", 1, "sunssf", None),
    ("ChaState_SF", 1, "sunssf", None),
    ("StorAval_SF", 1, "sunssf", None),
    ("InBatV_SF", 1, "sunssf", None),
    ("InOutWRte_SF", 1, "sunssf", None),
)

# SunSpec model 203, three-phase wye meter. MTR_ keys are profile identifiers
# that distinguish these points from identically named inverter/storage points.
# Model layout is from the official SunSpec models repository, model_203.json.
METER_POINTS = (
    ("MTR_A", 1, "int16", "MTR_A_SF"),
    ("MTR_AphA", 1, "int16", "MTR_A_SF"),
    ("MTR_AphB", 1, "int16", "MTR_A_SF"),
    ("MTR_AphC", 1, "int16", "MTR_A_SF"),
    ("MTR_A_SF", 1, "sunssf", None),
    ("MTR_PhV", 1, "int16", "MTR_V_SF"),
    ("MTR_PhVphA", 1, "int16", "MTR_V_SF"),
    ("MTR_PhVphB", 1, "int16", "MTR_V_SF"),
    ("MTR_PhVphC", 1, "int16", "MTR_V_SF"),
    ("MTR_PPV", 1, "int16", "MTR_V_SF"),
    ("MTR_PPVphAB", 1, "int16", "MTR_V_SF"),
    ("MTR_PPVphBC", 1, "int16", "MTR_V_SF"),
    ("MTR_PPVphCA", 1, "int16", "MTR_V_SF"),
    ("MTR_V_SF", 1, "sunssf", None),
    ("MTR_Hz", 1, "int16", "MTR_Hz_SF"),
    ("MTR_Hz_SF", 1, "sunssf", None),
    ("MTR_W", 1, "int16", "MTR_W_SF"),
    ("MTR_WphA", 1, "int16", "MTR_W_SF"),
    ("MTR_WphB", 1, "int16", "MTR_W_SF"),
    ("MTR_WphC", 1, "int16", "MTR_W_SF"),
    ("MTR_W_SF", 1, "sunssf", None),
    ("MTR_VA", 1, "int16", "MTR_VA_SF"),
    ("MTR_VAphA", 1, "int16", "MTR_VA_SF"),
    ("MTR_VAphB", 1, "int16", "MTR_VA_SF"),
    ("MTR_VAphC", 1, "int16", "MTR_VA_SF"),
    ("MTR_VA_SF", 1, "sunssf", None),
    ("MTR_VAR", 1, "int16", "MTR_VAR_SF"),
    ("MTR_VARphA", 1, "int16", "MTR_VAR_SF"),
    ("MTR_VARphB", 1, "int16", "MTR_VAR_SF"),
    ("MTR_VARphC", 1, "int16", "MTR_VAR_SF"),
    ("MTR_VAR_SF", 1, "sunssf", None),
    ("MTR_PF", 1, "int16", "MTR_PF_SF"),
    ("MTR_PFphA", 1, "int16", "MTR_PF_SF"),
    ("MTR_PFphB", 1, "int16", "MTR_PF_SF"),
    ("MTR_PFphC", 1, "int16", "MTR_PF_SF"),
    ("MTR_PF_SF", 1, "sunssf", None),
    ("MTR_TotWhExp", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhExpPhA", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhExpPhB", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhExpPhC", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhImp", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhImpPhA", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhImpPhB", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWhImpPhC", 2, "acc32", "MTR_TotWh_SF"),
    ("MTR_TotWh_SF", 1, "sunssf", None),
    ("MTR_TotVAhExp", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhExpPhA", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhExpPhB", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhExpPhC", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhImp", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhImpPhA", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhImpPhB", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAhImpPhC", 2, "acc32", "MTR_TotVAh_SF"),
    ("MTR_TotVAh_SF", 1, "sunssf", None),
    ("MTR_TotVArhImpQ1", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ1PhA", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ1PhB", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ1PhC", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ2", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ2PhA", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ2PhB", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhImpQ2PhC", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ3", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ3PhA", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ3PhB", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ3PhC", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ4", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ4PhA", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ4PhB", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArhExpQ4PhC", 2, "acc32", "MTR_TotVArh_SF"),
    ("MTR_TotVArh_SF", 1, "sunssf", None),
    ("MTR_Evt", 2, "bitfield32", None),
)

ALL_POINTS = (*INVERTER_POINTS, *STORAGE_POINTS, *METER_POINTS)
POINTS = {name: (width, kind, scale) for name, width, kind, scale in ALL_POINTS}
MODEL_POINTS = (
    (103, "Inverter", INVERTER_POINTS),
    (124, "Storage", STORAGE_POINTS),
    (203, "Meter", METER_POINTS),
)
POINT_LABELS = {
    (103, "W"): ("AC active power", "W"),
    (103, "Hz"): ("Grid frequency", "Hz"),
    (103, "WH"): ("Lifetime PV generation", "kWh"),
    (124, "ChaState"): ("Battery state of charge", "%"),
    (124, "InBatV"): ("Battery voltage", "V"),
    (203, "MTR_W"): ("Net grid power", "W"),
    (203, "MTR_WphA"): ("Grid power phase A", "W"),
    (203, "MTR_WphB"): ("Grid power phase B", "W"),
    (203, "MTR_WphC"): ("Grid power phase C", "W"),
}
POINT_UNITS = {
    "A": "A",
    "VA": "VA",
    "VAr": "var",
    "VAR": "var",
    "V": "V",
    "W": "W",
    "Hz": "Hz",
    "VA": "VA",
    "PF": "%",
    "WH": "Wh",
    "Tmp": "°C",
    "ChaState": "%",
    "InBatV": "V",
}
SCALE_FACTOR_POINTS = {
    scale
    for _, _, _, scale in ALL_POINTS
    if scale is not None
}
SOURCE_TYPES = {
    "uint16": (1, False),
    "int16": (1, True),
    "uint32": (2, False),
    "int32": (2, True),
}


def load_register_map(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        LOGGER.warning("Register map file does not exist: %s", path)
        config = {"version": 1, "fields": {}}
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to load register map {path}: {error}") from error

    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Register map must be a JSON object with version: 1")
    fields = config.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("Register map 'fields' must be a JSON object")
    scale_factors = config.get("scale_factors", {})
    if not isinstance(scale_factors, dict):
        raise ValueError("Register map 'scale_factors' must be a JSON object")

    validated_fields: dict[str, dict[str, Any]] = {}
    for name, source in fields.items():
        if name not in POINTS:
            raise ValueError(f"Unknown SunSpec point in register map: {name}")
        if not isinstance(source, dict):
            raise ValueError(f"Register map entry for {name} must be an object")
        register_type = source.get("register_type")
        address = source.get("address")
        data_type = source.get("data_type")
        scale = source.get("scale", 1)
        if register_type not in {"input", "holding"}:
            raise ValueError(f"{name}: register_type must be 'input' or 'holding'")
        if type(address) is not int or not 0 <= address <= 65535:
            raise ValueError(f"{name}: address must be an integer from 0 to 65535")
        if data_type not in SOURCE_TYPES:
            raise ValueError(f"{name}: unsupported data_type {data_type!r}")
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not math.isfinite(scale)
        ):
            raise ValueError(f"{name}: scale must be a finite number")
        width, _ = SOURCE_TYPES[data_type]
        if address + width > 65536:
            raise ValueError(f"{name}: source register range exceeds Modbus address space")
        _, target_kind, scale_point = POINTS[name]
        if target_kind == "sunssf":
            raise ValueError(f"{name}: scale-factor points are configured under scale_factors")
        word_order = source.get("word_order", "big")
        if word_order not in {"big", "swap"}:
            raise ValueError(f"{name}: word_order must be 'big' or 'swap'")
        invalid_values = source.get("invalid_values", [])
        if (
            not isinstance(invalid_values, list)
            or any(type(value) is not int for value in invalid_values)
        ):
            raise ValueError(f"{name}: invalid_values must be a list of integers")
        validated_fields[name] = {
            "register_type": register_type,
            "address": address,
            "data_type": data_type,
            "scale": float(scale),
            "scale_point": scale_point,
            "word_order": word_order,
            "invalid_values": invalid_values,
        }

    validated_scale_factors: dict[str, int] = {}
    for name, exponent in scale_factors.items():
        if name not in SCALE_FACTOR_POINTS:
            raise ValueError(f"Unknown SunSpec scale factor: {name}")
        if type(exponent) is not int or not -10 <= exponent <= 10:
            raise ValueError(f"{name}: scale factor must be an integer from -10 to 10")
        validated_scale_factors[name] = exponent

    device_address = config.get("device_address", 1)
    if type(device_address) is not int or not 0 <= device_address <= 65535:
        raise ValueError("device_address must be an integer from 0 to 65535")

    return {
        "fields": validated_fields,
        "scale_factors": validated_scale_factors,
        "common": {
            "manufacturer": str(config.get("manufacturer", "Sungrow")),
            "model": str(config.get("model", "SH25T")),
            "options": str(config.get("options", "SHB")),
            "version": str(config.get("version_string", "")),
            "serial_number": str(config.get("serial_number", "")),
            "device_address": device_address,
        },
    }


def _not_implemented(kind: str) -> list[int]:
    if kind in {"uint16", "enum16", "bitfield16"}:
        return [0xFFFF]
    if kind in {"int16", "sunssf"}:
        return [0x8000]
    if kind in {"acc32", "bitfield32"}:
        return [0xFFFF, 0xFFFF]
    raise ValueError(f"Unsupported SunSpec type: {kind}")


def _encode_point(value: float | int, kind: str, width: int) -> list[int]:
    if kind in {"uint16", "enum16", "bitfield16"}:
        integer = round(value)
        if not 0 <= integer <= 0xFFFE:
            raise ValueError(f"{kind} value outside range: {value}")
        return [integer]
    if kind in {"int16", "sunssf"}:
        integer = round(value)
        if not -0x7FFF <= integer <= 0x7FFF:
            raise ValueError(f"{kind} value outside range: {value}")
        return [integer & 0xFFFF]
    if kind in {"acc32", "bitfield32"} and width == 2:
        integer = round(value)
        if not 0 <= integer <= 0xFFFFFFFE:
            raise ValueError(f"{kind} value outside range: {value}")
        return [(integer >> 16) & 0xFFFF, integer & 0xFFFF]
    raise ValueError(f"Unsupported SunSpec type/width: {kind}/{width}")


def _encode_string(value: str, words: int) -> list[int]:
    raw = value.encode("ascii", errors="replace")[: words * 2].ljust(words * 2, b"\x00")
    return [(raw[index] << 8) | raw[index + 1] for index in range(0, len(raw), 2)]


def build_registers(
    mappings: dict[str, Any],
    source_values: dict[str, int | float],
    base_address: int = 40000,
) -> dict[int, int]:
    """Build SunSpec Common, three-phase inverter, and storage model registers."""
    data: list[int] = [0x5375, 0x6E53]
    data.extend((1, 66))
    common = mappings["common"]
    for key, width in (
        ("manufacturer", 16),
        ("model", 16),
        ("options", 8),
        ("version", 8),
        ("serial_number", 16),
    ):
        data.extend(_encode_string(common[key], width))
    data.extend((common["device_address"] & 0xFFFF, 0))

    for model_id, points in (
        (103, INVERTER_POINTS),
        (124, STORAGE_POINTS),
        (203, METER_POINTS),
    ):
        data.extend((model_id, sum(point[1] for point in points)))
        for name, width, kind, scale_point in points:
            if kind == "sunssf":
                value = mappings["scale_factors"].get(name, 0)
                data.extend(_encode_point(value, kind, width))
                continue
            if name not in source_values:
                data.extend(_not_implemented(kind))
                continue
            value = source_values[name]
            if scale_point is not None:
                exponent = mappings["scale_factors"].get(scale_point, 0)
                value = value / (10**exponent)
            data.extend(_encode_point(value, kind, width))

    data.append(0xFFFF)
    if len(data) + base_address > 65536:
        raise ValueError("SunSpec register map exceeds Modbus address space")
    return {base_address + index: word for index, word in enumerate(data)}


def build_dashboard_data(
    mappings: dict[str, Any],
    source_values: dict[str, int | float],
    *,
    updated_at: str | None,
    error: bool,
) -> dict[str, Any]:
    common = mappings["common"]
    models: list[dict[str, Any]] = [
        {
            "id": 1,
            "name": "Common",
            "points": [
                {"name": label, "label": label, "value": common[key], "unit": "", "available": True}
                for key, label in (
                    ("manufacturer", "Manufacturer"),
                    ("model", "Model"),
                    ("options", "Options"),
                    ("version", "Firmware"),
                    ("serial_number", "Serial number"),
                    ("device_address", "Device address"),
                )
            ],
        }
    ]

    for model_id, model_name, points in MODEL_POINTS:
        model_points: list[dict[str, Any]] = []
        for name, _width, kind, scale_point in points:
            is_scale_factor = kind == "sunssf"
            available = is_scale_factor or name in source_values
            value = (
                mappings["scale_factors"].get(name, 0)
                if is_scale_factor
                else source_values.get(name)
            )
            label, unit = POINT_LABELS.get(
                (model_id, name),
                (name.removeprefix("MTR_"), ""),
            )
            if not unit:
                canonical_name = name.removeprefix("MTR_")
                unit = next(
                    (
                        known_unit
                        for prefix, known_unit in POINT_UNITS.items()
                        if canonical_name.startswith(prefix)
                    ),
                    "",
                )
            if is_scale_factor:
                label, unit = f"{name} scale factor", "10^x"
            elif scale_point is not None:
                if not unit:
                    unit = "engineering units"
                if available:
                    exponent = mappings["scale_factors"].get(scale_point, 0)
                    value = round(value / (10**exponent)) * (10**exponent)
            if model_id == 103 and name == "WH" and available:
                value = round(value / 1000, 1)
            model_points.append(
                {
                    "name": name,
                    "label": label,
                    "value": value,
                    "unit": unit,
                    "available": available,
                }
            )
        models.append({"id": model_id, "name": model_name, "points": model_points})

    return {
        "status": (
            "unavailable"
            if error
            else (
                "waiting"
                if updated_at is None or not mappings["fields"]
                else "online"
            )
        ),
        "updated_at": updated_at,
        "models": models,
        "summary": [
            {"model": model_id, "point": name, "label": label}
            for model_id, name, label in (
                (103, "W", "Inverter power"),
                (124, "ChaState", "Battery charge"),
                (203, "MTR_W", "Grid power"),
            )
        ],
    }
