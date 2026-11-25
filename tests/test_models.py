import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "sungrow_sunspec" / "app"))

from models import (
    INVERTER_POINTS,
    METER_POINTS,
    STORAGE_POINTS,
    build_dashboard_data,
    build_registers,
    load_register_map,
)


def empty_map():
    return {
        "fields": {},
        "scale_factors": {},
        "common": {
            "manufacturer": "Sungrow",
            "model": "SH25T",
            "options": "SHB",
            "version": "",
            "serial_number": "",
            "device_address": 1,
        },
    }


class RegisterMapTests(unittest.TestCase):
    def test_dashboard_reports_scaled_mapped_values_and_not_implemented_points(self):
        mappings = empty_map()
        mappings["fields"] = {"MTR_W": {}, "ChaState": {}}
        mappings["scale_factors"] = {"ChaState_SF": -1}
        data = build_dashboard_data(
            mappings,
            {"MTR_W": -325, "ChaState": 61.23},
            updated_at="2025-01-01T00:00:00+00:00",
            error=False,
        )
        self.assertEqual(data["status"], "online")
        meter = next(model for model in data["models"] if model["id"] == 203)
        grid_power = next(point for point in meter["points"] if point["name"] == "MTR_W")
        self.assertEqual(
            (grid_power["label"], grid_power["value"], grid_power["unit"], grid_power["available"]),
            ("Net grid power", -325, "W", True),
        )
        storage = next(model for model in data["models"] if model["id"] == 124)
        battery_charge = next(
            point for point in storage["points"] if point["name"] == "ChaState"
        )
        self.assertEqual(battery_charge["value"], 61.2)
        self.assertEqual(battery_charge["unit"], "%")
        self.assertFalse(
            next(point for point in meter["points"] if point["name"] == "MTR_A")[
                "available"
            ]
        )

    def test_dashboard_marks_points_unavailable_after_poll_error(self):
        data = build_dashboard_data(
            empty_map(), {}, updated_at=None, error=True
        )
        self.assertEqual(data["status"], "unavailable")
        meter = next(model for model in data["models"] if model["id"] == 203)
        self.assertIsNone(
            next(point for point in meter["points"] if point["name"] == "MTR_W")["value"]
        )

    def test_live_common_values_override_profile_fallbacks_individually(self):
        mappings = empty_map()
        common_values = {
            "manufacturer": "Live Manufacturer",
            "model": "Live Model",
            "device_address": 7,
        }
        data = build_dashboard_data(
            mappings,
            {},
            updated_at="2025-01-01T00:00:00+00:00",
            error=False,
            common_values=common_values,
        )
        common_points = {
            point["label"]: point["value"] for point in data["models"][0]["points"]
        }
        self.assertEqual(common_points["Manufacturer"], "Live Manufacturer")
        self.assertEqual(common_points["Model"], "Live Model")
        self.assertEqual(common_points["Options"], "SHB")
        self.assertEqual(common_points["Device address"], 7)

        registers = build_registers(mappings, {}, common_values=common_values)
        encoded_manufacturer = b"".join(
            registers[40004 + index].to_bytes(2, "big") for index in range(16)
        )
        self.assertEqual(
            encoded_manufacturer.split(b"\x00", 1)[0].decode("ascii"),
            "Live Manufacturer",
        )
        self.assertEqual(registers[40068], 7)

    def test_dashboard_displays_scale_factors_as_readable_multipliers(self):
        mappings = empty_map()
        mappings["scale_factors"] = {"A_SF": -1, "W_SF": 0}
        data = build_dashboard_data(
            mappings, {}, updated_at=None, error=False
        )
        inverter = next(model for model in data["models"] if model["id"] == 103)
        points = {point["name"]: point for point in inverter["points"]}
        self.assertEqual(
            (
                points["A_SF"]["label"],
                points["A_SF"]["value"],
                points["A_SF"]["unit"],
            ),
            ("Current scale multiplier", "×0.1", ""),
        )
        self.assertEqual(
            (
                points["W_SF"]["label"],
                points["W_SF"]["value"],
                points["W_SF"]["unit"],
            ),
            ("Active power scale multiplier", "×1", ""),
        )

    def test_dashboard_displays_lifetime_energy_in_kwh_but_sunspec_stays_in_wh(self):
        mappings = empty_map()
        mappings["fields"] = {"WH": {}}
        energy_wh = 13_085_500

        data = build_dashboard_data(
            mappings, {"WH": energy_wh}, updated_at="2025-01-01T00:00:00+00:00", error=False
        )
        inverter = next(model for model in data["models"] if model["id"] == 103)
        energy = next(point for point in inverter["points"] if point["name"] == "WH")
        self.assertEqual(energy["label"], "Lifetime PV generation")
        self.assertEqual(energy["value"], 13_085.5)
        self.assertEqual(energy["unit"], "kWh")

        registers = build_registers(mappings, {"WH": energy_wh})
        data_start = 40000 + 4 + 66 + 2
        energy_offset = sum(
            point[1]
            for point in INVERTER_POINTS[: next(
                index for index, point in enumerate(INVERTER_POINTS) if point[0] == "WH"
            )]
        )
        encoded_wh = (registers[data_start + energy_offset] << 16) | registers[
            data_start + energy_offset + 1
        ]
        self.assertEqual(encoded_wh, energy_wh)

    def test_sunspec_headers_and_model_lengths(self):
        registers = build_registers(empty_map(), {})
        self.assertEqual(registers[40000], 0x5375)
        self.assertEqual(registers[40001], 0x6E53)
        self.assertEqual((registers[40002], registers[40003]), (1, 66))

        model_103_header = 40000 + 4 + 66
        self.assertEqual((registers[model_103_header], registers[model_103_header + 1]), (103, 50))
        model_124_header = model_103_header + 2 + sum(point[1] for point in INVERTER_POINTS)
        self.assertEqual((registers[model_124_header], registers[model_124_header + 1]), (124, 24))
        model_203_header = model_124_header + 2 + sum(point[1] for point in STORAGE_POINTS)
        self.assertEqual(
            (registers[model_203_header], registers[model_203_header + 1]), (203, 105)
        )
        self.assertEqual(sum(point[1] for point in METER_POINTS), 105)
        self.assertEqual(registers[max(registers)], 0xFFFF)
        self.assertEqual(sum(point[1] for point in STORAGE_POINTS), 24)

    def test_selected_model_is_exposed_after_common_model(self):
        registers = build_registers(empty_map(), {}, exposed_models=(124,))
        self.assertEqual((registers[40070], registers[40071]), (124, 24))
        self.assertEqual(registers[40096], 0xFFFF)
        self.assertEqual(len(registers), 97)

    def test_invalid_exposed_model_selection_is_rejected(self):
        for selected in ((999,), (103, 103), (True,)):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                build_registers(empty_map(), {}, exposed_models=selected)

    def test_mapped_points_are_scaled_and_unmapped_are_sentinel(self):
        mappings = empty_map()
        mappings["scale_factors"] = {"W_SF": -1}
        registers = build_registers(mappings, {"W": 2500})
        model_103_data = 40000 + 4 + 66 + 2
        w_offset = next(
            sum(point[1] for point in INVERTER_POINTS[:index])
            for index, point in enumerate(INVERTER_POINTS)
            if point[0] == "W"
        )
        self.assertEqual(registers[model_103_data + w_offset], 25000)
        self.assertEqual(registers[model_103_data + w_offset + 1], 0xFFFF)

    def test_register_map_validation_and_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "register_map.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "fields": {
                            "W": {
                                "register_type": "input",
                                "address": 100,
                                "data_type": "int16",
                                "scale": 0.1,
                            }
                        },
                        "scale_factors": {"W_SF": 0},
                    }
                ),
                encoding="utf-8",
            )
            result = load_register_map(path)
            self.assertEqual(result["fields"]["W"]["address"], 100)
            self.assertEqual(result["fields"]["W"]["scale"], 0.1)

    def test_invalid_point_is_rejected_and_wider_source_can_feed_narrow_point(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "register_map.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "fields": {
                            "invented": {
                                "register_type": "input",
                                "address": 10,
                                "data_type": "uint16",
                            }
                        },
                    }
                )
            )
            with self.assertRaises(ValueError):
                load_register_map(path)

            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "fields": {
                            "W": {
                                "register_type": "input",
                                "address": 10,
                                "data_type": "int32",
                                "word_order": "swap",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            loaded = load_register_map(path)
            self.assertEqual(loaded["fields"]["W"]["data_type"], "int32")
            self.assertEqual(loaded["fields"]["W"]["word_order"], "swap")

    def test_bundled_community_profile_has_expected_provenance_and_points(self):
        profile_path = (
            Path(__file__).parents[1]
            / "addon"
            / "sungrow_sunspec"
            / "profiles"
            / "sh25t_shb.community.json"
        )
        mappings = load_register_map(profile_path)
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertIn("mkaiser", profile["profile_source"])
        self.assertEqual(
            profile["profile_source_revision"],
            "071f8c8c5f784198928f80de23ae168eed1acd1d",
        )
        self.assertEqual(mappings["fields"]["W"]["address"], 13033)
        self.assertEqual(mappings["fields"]["W"]["word_order"], "swap")
        self.assertEqual(mappings["fields"]["PF"]["scale"], 0.1)
        self.assertEqual(mappings["fields"]["WH"]["scale"], 100)
        self.assertEqual(mappings["fields"]["MTR_W"]["address"], 5600)
        self.assertEqual(mappings["fields"]["MTR_W"]["invalid_values"], [2147483647])
        self.assertEqual(mappings["fields"]["MTR_TotWhImp"]["address"], 13036)
        self.assertEqual(mappings["fields"]["MTR_TotWhImp"]["scale"], 100)
        self.assertEqual(mappings["fields"]["MTR_TotWhImp"]["word_order"], "swap")
        self.assertEqual(mappings["fields"]["MTR_TotWhExp"]["address"], 13045)
        self.assertEqual(mappings["fields"]["MTR_TotWhExp"]["scale"], 100)
        self.assertEqual(mappings["fields"]["MTR_TotWhExp"]["word_order"], "swap")

    def test_community_profile_values_encode_at_documented_sunspec_points(self):
        profile_path = (
            Path(__file__).parents[1]
            / "addon"
            / "sungrow_sunspec"
            / "profiles"
            / "sh25t_shb.community.json"
        )
        mappings = load_register_map(profile_path)
        registers = build_registers(
            mappings,
            {"W": 2500, "PF": 95, "WH": 1_234_500, "ChaState": 67.5},
        )
        model_103_header = 40000 + 4 + 66
        model_103_data = model_103_header + 2
        inverter_offsets = {
            point[0]: sum(item[1] for item in INVERTER_POINTS[:index])
            for index, point in enumerate(INVERTER_POINTS)
        }
        self.assertEqual(registers[model_103_data + inverter_offsets["W"]], 2500)
        self.assertEqual(registers[model_103_data + inverter_offsets["PF"]], 9500)
        self.assertEqual(registers[model_103_data + inverter_offsets["WH"]], 0x0012)
        self.assertEqual(registers[model_103_data + inverter_offsets["WH"] + 1], 0xD644)

        model_124_header = (
            model_103_header + 2 + sum(point[1] for point in INVERTER_POINTS)
        )
        model_124_data = model_124_header + 2
        storage_offsets = {
            point[0]: sum(item[1] for item in STORAGE_POINTS[:index])
            for index, point in enumerate(STORAGE_POINTS)
        }
        self.assertEqual(
            registers[model_124_data + storage_offsets["ChaState"]], 675
        )

    def test_meter_model_exposes_signed_import_and_export(self):
        mappings = load_register_map(
            Path(__file__).parents[1]
            / "addon"
            / "sungrow_sunspec"
            / "profiles"
            / "sh25t_shb.community.json"
        )
        model_203_header = (
            40000
            + 4
            + 66
            + 2
            + sum(point[1] for point in INVERTER_POINTS)
            + 2
            + sum(point[1] for point in STORAGE_POINTS)
        )
        model_203_data = model_203_header + 2
        meter_offsets = {
            point[0]: sum(item[1] for item in METER_POINTS[:index])
            for index, point in enumerate(METER_POINTS)
        }
        registers = build_registers(
            mappings,
            {"MTR_W": 420, "MTR_WphA": 200, "MTR_WphB": 120, "MTR_WphC": 100},
        )
        self.assertEqual(registers[model_203_data + meter_offsets["MTR_W"]], 420)
        self.assertEqual(registers[model_203_data + meter_offsets["MTR_W_SF"]], 0)
        registers = build_registers(
            mappings,
            {
                "MTR_W": -2500,
                "MTR_WphA": -1000,
                "MTR_WphB": -800,
                "MTR_WphC": -700,
            },
        )
        self.assertEqual(
            registers[model_203_data + meter_offsets["MTR_W"]], 0xF63C
        )

    def test_meter_model_exposes_total_grid_import_and_export_energy(self):
        profile_path = (
            Path(__file__).parents[1]
            / "addon"
            / "sungrow_sunspec"
            / "profiles"
            / "sh25t_shb.community.json"
        )
        mappings = load_register_map(profile_path)
        meter_data = {
            "MTR_TotWhImp": 1_234_500,
            "MTR_TotWhExp": 987_600,
        }
        data = build_dashboard_data(
            mappings, meter_data, updated_at="2025-01-01T00:00:00+00:00", error=False
        )
        meter = next(model for model in data["models"] if model["id"] == 203)
        points = {point["name"]: point for point in meter["points"]}
        self.assertEqual(
            (
                points["MTR_TotWhImp"]["label"],
                points["MTR_TotWhImp"]["value"],
                points["MTR_TotWhImp"]["unit"],
            ),
            ("Total grid import", 1234.5, "kWh"),
        )
        self.assertEqual(
            (
                points["MTR_TotWhExp"]["label"],
                points["MTR_TotWhExp"]["value"],
                points["MTR_TotWhExp"]["unit"],
            ),
            ("Total grid export", 987.6, "kWh"),
        )

        model_203_header = (
            40000
            + 4
            + 66
            + 2
            + sum(point[1] for point in INVERTER_POINTS)
            + 2
            + sum(point[1] for point in STORAGE_POINTS)
        )
        model_203_data = model_203_header + 2
        meter_offsets = {
            point[0]: sum(item[1] for item in METER_POINTS[:index])
            for index, point in enumerate(METER_POINTS)
        }
        registers = build_registers(mappings, meter_data)
        for name, value in meter_data.items():
            self.assertEqual(
                (registers[model_203_data + meter_offsets[name]] << 16)
                | registers[model_203_data + meter_offsets[name] + 1],
                value,
            )


if __name__ == "__main__":
    unittest.main()
