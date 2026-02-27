from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.modules import refresh_start

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
        "min_healthy_percentage": 90,
        "max_healthy_percentage": 110,
        "instance_warmup": 300,
        "no_skip_matching": False,
        "checkpoint_percentages": None,
        "checkpoint_delay": 3600,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestValidation:
    def test_max_healthy_below_100_exits_3(self):
        with pytest.raises(SystemExit) as exc:
            refresh_start.start(_make_args(max_healthy_percentage=99), _CONFIG)
        assert exc.value.code == 3

    def test_max_healthy_above_200_exits_3(self):
        with pytest.raises(SystemExit) as exc:
            refresh_start.start(_make_args(max_healthy_percentage=201), _CONFIG)
        assert exc.value.code == 3

    def test_min_greater_than_max_exits_3(self):
        with pytest.raises(SystemExit) as exc:
            refresh_start.start(
                _make_args(min_healthy_percentage=150, max_healthy_percentage=100),
                _CONFIG,
            )
        assert exc.value.code == 3


class TestAwsErrors:
    @patch("src.modules.refresh_start.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_start.boto3.client")
    def test_client_error_exits_2(self, mock_boto, mock_lookup):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_instance_refresh.side_effect = ClientError(
            {"Error": {"Code": "AlreadyExists", "Message": "already running"}},
            "StartInstanceRefresh",
        )
        with pytest.raises(SystemExit) as exc:
            refresh_start.start(_make_args(), _CONFIG)
        assert exc.value.code == 2


class TestArtifact:
    @patch("src.modules.refresh_start.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_start.boto3.client")
    @patch("src.modules.refresh_start.os.makedirs")
    @patch("builtins.open", side_effect=OSError("disk full"))
    def test_oserror_on_write_exits_4(
        self, mock_open, mock_makedirs, mock_boto, mock_lookup
    ):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_instance_refresh.return_value = {
            "InstanceRefreshId": "abc-123"
        }
        with pytest.raises(SystemExit) as exc:
            refresh_start.start(_make_args(), _CONFIG)
        assert exc.value.code == 4

    @patch("src.modules.refresh_start.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_start.boto3.client")
    def test_success_exits_0_and_writes_artifact(
        self, mock_boto, mock_lookup, tmp_path
    ):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_instance_refresh.return_value = {
            "InstanceRefreshId": "abc-123"
        }
        config = {
            "artifacts": {
                "output_dir": str(tmp_path / "outputs"),
                "refresh_env_filename": "refresh.env",
            }
        }
        with pytest.raises(SystemExit) as exc:
            refresh_start.start(_make_args(), config)
        assert exc.value.code == 0
        artifact = (tmp_path / "outputs" / "refresh.env").read_text()
        assert artifact == "INSTANCE_REFRESH_ID=abc-123\n"


class TestPreferences:
    @patch("src.modules.refresh_start.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_start.boto3.client")
    def test_checkpoint_percentages_included(self, mock_boto, mock_lookup, tmp_path):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_instance_refresh.return_value = {
            "InstanceRefreshId": "abc-123"
        }
        config = {
            "artifacts": {
                "output_dir": str(tmp_path / "outputs"),
                "refresh_env_filename": "refresh.env",
            }
        }
        args = _make_args(checkpoint_percentages=[50, 100], checkpoint_delay=1800)
        with pytest.raises(SystemExit):
            refresh_start.start(args, config)
        prefs = mock_client.start_instance_refresh.call_args.kwargs["Preferences"]
        assert prefs["CheckpointPercentages"] == [50, 100]
        assert prefs["CheckpointDelay"] == 1800

    @patch("src.modules.refresh_start.lookup_asg", return_value="my-asg")
    @patch("src.modules.refresh_start.boto3.client")
    def test_no_skip_matching_sets_false(self, mock_boto, mock_lookup, tmp_path):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.start_instance_refresh.return_value = {
            "InstanceRefreshId": "abc-123"
        }
        config = {
            "artifacts": {
                "output_dir": str(tmp_path / "outputs"),
                "refresh_env_filename": "refresh.env",
            }
        }
        with pytest.raises(SystemExit):
            refresh_start.start(_make_args(no_skip_matching=True), config)
        prefs = mock_client.start_instance_refresh.call_args.kwargs["Preferences"]
        assert prefs["SkipMatching"] is False
