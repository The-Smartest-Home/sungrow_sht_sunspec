import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "addon" / "sungrow_sunspec" / "app"))

from main import read_options, resolve_register_map_path


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
                '"web_port":8080,'
                '"allowed_clients":"127.0.0.1/32",'
                '"register_map_file":"/app/profiles/default.json"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "inverter_port"):
                read_options(options_file)


if __name__ == "__main__":
    unittest.main()
