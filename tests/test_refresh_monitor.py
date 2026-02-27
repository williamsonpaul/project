from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.modules import refresh_monitor

_CONFIG = {
    "artifacts": {
        "output_dir": "outputs",
        "refresh_env_filename": "refresh.env",
    }
}


def _make_args(**kwargs):
    defaults = {
        "tag_key": "Name",
        "tag_value": "my-asg",
        "refresh_id": None,
        "poll_interval": 30,
        "timeout": 1800,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


def _describe_response(status, pct=50):
    return {
        "InstanceRefreshes": [
            {
                "InstanceRefreshId": "rid-1",
                "Status": status,
                "PercentageComplete": pct,
            }
        ]
    }


class TestRefreshIdResolution:
    @patch("src.modules.refresh_monitor.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_monitor.boto3.client")
    @patch("src.modules.refresh_monitor.time.sleep")
    @patch(
        "src.modules.refresh_monitor.time.monotonic",
        side_effect=[0, 0],
    )
    def test_refresh_id_from_arg(self, mock_mono, mock_sleep, mock_boto, mock_lookup):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.describe_instance_refreshes.return_value = _describe_response(
            "Successful"
        )
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(refresh_id="explicit-id"), _CONFIG)
        assert exc.value.code == 0
        call_kwargs = mock_client.describe_instance_refreshes.call_args.kwargs
        assert call_kwargs["InstanceRefreshIds"] == ["explicit-id"]

    @patch("src.modules.refresh_monitor.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_monitor.boto3.client")
    @patch("src.modules.refresh_monitor.time.sleep")
    @patch(
        "src.modules.refresh_monitor.time.monotonic",
        side_effect=[0, 0],
    )
    def test_refresh_id_from_artifact(
        self, mock_mono, mock_sleep, mock_boto, mock_lookup, tmp_path
    ):
        artifact_dir = tmp_path / "outputs"
        artifact_dir.mkdir()
        (artifact_dir / "refresh.env").write_text("INSTANCE_REFRESH_ID=art-id\n")
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.describe_instance_refreshes.return_value = _describe_response(
            "Successful"
        )
        config = {
            "artifacts": {
                "output_dir": str(artifact_dir),
                "refresh_env_filename": "refresh.env",
            }
        }
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(), config)
        assert exc.value.code == 0
        call_kwargs = mock_client.describe_instance_refreshes.call_args.kwargs
        assert call_kwargs["InstanceRefreshIds"] == ["art-id"]

    def test_missing_refresh_id_exits_3(self):
        config = {
            "artifacts": {
                "output_dir": "/nonexistent/path",
                "refresh_env_filename": "refresh.env",
            }
        }
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(), config)
        assert exc.value.code == 3


class TestLookupFailure:
    @patch("src.modules.refresh_monitor.lookup_asg", side_effect=SystemExit(1))
    @patch("src.modules.refresh_monitor.boto3.client")
    def test_lookup_systemexit_becomes_2(self, mock_boto, mock_lookup):
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(refresh_id="rid"), _CONFIG)
        assert exc.value.code == 2


class TestTerminalStates:
    @pytest.mark.parametrize(
        "status,expected_code",
        [
            ("Successful", 0),
            ("Failed", 1),
            ("Cancelled", 2),
            ("RollbackSuccessful", 4),
            ("RollbackFailed", 5),
        ],
    )
    @patch("src.modules.refresh_monitor.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_monitor.boto3.client")
    @patch("src.modules.refresh_monitor.time.sleep")
    @patch(
        "src.modules.refresh_monitor.time.monotonic",
        side_effect=[0, 0],
    )
    def test_terminal_state_exit_code(
        self,
        mock_mono,
        mock_sleep,
        mock_boto,
        mock_lookup,
        status,
        expected_code,
    ):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.describe_instance_refreshes.return_value = _describe_response(
            status
        )
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(refresh_id="rid"), _CONFIG)
        assert exc.value.code == expected_code


class TestErrorConditions:
    @patch("src.modules.refresh_monitor.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_monitor.boto3.client")
    @patch(
        "src.modules.refresh_monitor.time.monotonic",
        side_effect=[0, 1800],
    )
    def test_timeout_exits_3(self, mock_mono, mock_boto, mock_lookup):
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(refresh_id="rid", timeout=1800), _CONFIG)
        assert exc.value.code == 3

    @patch("src.modules.refresh_monitor.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_monitor.boto3.client")
    @patch("src.modules.refresh_monitor.time.sleep")
    @patch(
        "src.modules.refresh_monitor.time.monotonic",
        side_effect=[0, 0],
    )
    def test_client_error_exits_2(self, mock_mono, mock_sleep, mock_boto, mock_lookup):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.describe_instance_refreshes.side_effect = ClientError(
            {"Error": {"Code": "InvalidID", "Message": "not found"}},
            "DescribeInstanceRefreshes",
        )
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(refresh_id="rid"), _CONFIG)
        assert exc.value.code == 2

    @patch("src.modules.refresh_monitor.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_monitor.boto3.client")
    @patch("src.modules.refresh_monitor.time.sleep")
    @patch(
        "src.modules.refresh_monitor.time.monotonic",
        side_effect=[0, 0],
    )
    def test_empty_refreshes_exits_2(
        self, mock_mono, mock_sleep, mock_boto, mock_lookup
    ):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.describe_instance_refreshes.return_value = {"InstanceRefreshes": []}
        with pytest.raises(SystemExit) as exc:
            refresh_monitor.monitor(_make_args(refresh_id="rid"), _CONFIG)
        assert exc.value.code == 2
