import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "sungrow_sunspec" / "app"))

from main import get_ingress_port, read_options, resolve_register_map_path


class RegisterMapPathTests(unittest.TestCase):
    def test_accepts_files_from_profile_and_app_config_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            profile_directory = root / "profiles"
            config_directory = root / "config"
            profile_directory.mkdir()
            config_directory.mkdir()
            bundled_profile = profile_directory / "default.json"
            custom_profile = config_directory / "custom.json"
            bundled_profile.touch()
            custom_profile.touch()

            self.assertEqual(
                resolve_register_map_path(
                    str(bundled_profile), profile_directory, config_directory
                ),
                bundled_profile.resolve(),
            )
            self.assertEqual(
                resolve_register_map_path(
                    str(custom_profile), profile_directory, config_directory
                ),
                custom_profile.resolve(),
            )

    def test_rejects_files_outside_allowed_directories_and_missing_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            profile_directory = root / "profiles"
            config_directory = root / "config"
            outside_file = root / "secrets.json"
            profile_directory.mkdir()
            config_directory.mkdir()
            outside_file.touch()

            with self.assertRaisesRegex(ValueError, "inside /app/profiles or /config"):
                resolve_register_map_path(
                    str(outside_file), profile_directory, config_directory
                )
            with self.assertRaisesRegex(ValueError, "does not exist"):
                resolve_register_map_path(
                    str(config_directory / "missing.json"),
                    profile_directory,
                    config_directory,
                )

    def test_read_options_rejects_boolean_as_integer(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            options_file = Path(temporary_directory) / "options.json"
            options_file.write_text(
                '{"inverter_host":"192.168.1.2","inverter_port":true,'
                '"unit_id":1,"refresh_interval":5,"sunspec_port":5020,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "inverter_port"):
                read_options(options_file)

    def test_read_options_defaults_and_parses_model_checkboxes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            options_file = Path(temporary_directory) / "options.json"
            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json"}',
                encoding="utf-8",
            )
            self.assertEqual(read_options(options_file)["exposed_models"], (103, 124, 203))

            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json",'
                '"expose_model_103":true,"expose_model_124":false,'
                '"expose_model_203":true}',
                encoding="utf-8",
            )
            self.assertEqual(read_options(options_file)["exposed_models"], (103, 203))

            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json",'
                '"expose_model_103":false,"expose_model_124":false,'
                '"expose_model_203":false}',
                encoding="utf-8",
            )
            self.assertEqual(read_options(options_file)["exposed_models"], ())

    def test_read_options_migrates_legacy_model_selection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            options_file = Path(temporary_directory) / "options.json"
            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json",'
                '"exposed_models":"203,103"}',
                encoding="utf-8",
            )
            self.assertEqual(read_options(options_file)["exposed_models"], (103, 203))

            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json",'
                '"exposed_models":"124","expose_model_203":true}',
                encoding="utf-8",
            )
            self.assertEqual(read_options(options_file)["exposed_models"], (124, 203))

    def test_read_options_rejects_non_boolean_model_checkbox(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            options_file = Path(temporary_directory) / "options.json"
            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json",'
                '"expose_model_103":"true"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "expose_model_103"):
                read_options(options_file)

    def test_read_options_rejects_invalid_legacy_model_selection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            options_file = Path(temporary_directory) / "options.json"
            options_file.write_text(
                '{"inverter_host":"inverter.local","inverter_port":502,'
                '"unit_id":1,"refresh_interval":5,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json",'
                '"exposed_models":"103,999"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Legacy exposed_models"):
                read_options(options_file)

    @patch("main.urllib.request.urlopen")
    def test_get_ingress_port_uses_supervisor_info(self, urlopen):
        with patch("main.json.load", return_value={"data": {"ingress_port": 63124}}):
            self.assertEqual(
                get_ingress_port("test-token", url="http://supervisor/addons/self/info"),
                63124,
            )
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)

    def test_get_ingress_port_rejects_missing_token_and_invalid_response(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SUPERVISOR_TOKEN"):
                get_ingress_port()
        with patch("main.urllib.request.urlopen") as urlopen:
            response = urlopen.return_value.__enter__.return_value
            with patch("main.json.load", return_value={"data": {"ingress_port": 0}}):
                with self.assertRaisesRegex(RuntimeError, "invalid ingress port"):
                    get_ingress_port("test-token")


if __name__ == "__main__":
    unittest.main()
