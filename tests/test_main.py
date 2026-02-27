from unittest.mock import patch

import pytest

from src.main import load_config, main

_DEFAULTS = {
    "min_healthy_percentage": 90,
    "max_healthy_percentage": 100,
    "instance_warmup": 300,
    "poll_interval": 30,
    "timeout": 1800,
}


class TestLoadConfig:
    def test_loads_yaml_successfully(self):
        config = load_config()
        assert "defaults" in config
        assert "artifacts" in config
        defaults = config["defaults"]
        assert "min_healthy_percentage" in defaults
        assert "max_healthy_percentage" in defaults


class TestMain:
    @patch("src.main.refresh_start")
    @patch("src.main.load_config")
    def test_start_dispatch(self, mock_load_config, mock_refresh_start):
        mock_load_config.return_value = {
            "defaults": _DEFAULTS,
            "artifacts": {},
        }
        with patch(
            "sys.argv",
            ["main.py", "start", "--tag-key", "Name", "--tag-value", "my-asg"],
        ):
            main()
        mock_refresh_start.start.assert_called_once()

    @patch("src.main.refresh_monitor")
    @patch("src.main.load_config")
    def test_monitor_dispatch(self, mock_load_config, mock_refresh_monitor):
        mock_load_config.return_value = {
            "defaults": _DEFAULTS,
            "artifacts": {},
        }
        with patch(
            "sys.argv",
            ["main.py", "monitor", "--tag-key", "Name", "--tag-value", "my-asg"],
        ):
            main()
        mock_refresh_monitor.monitor.assert_called_once()

    @patch("src.main.load_config")
    def test_no_subcommand_exits_0(self, mock_load_config):
        mock_load_config.return_value = {"defaults": {}, "artifacts": {}}
        with patch("sys.argv", ["main.py"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0
