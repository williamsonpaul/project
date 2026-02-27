import json
from unittest.mock import MagicMock

import pytest

from src.modules.asg_lookup import _log, lookup_asg


def _make_asg(name, tags):
    return {
        "AutoScalingGroupName": name,
        "Tags": [{"Key": k, "Value": v} for k, v in tags.items()],
    }


def _make_client(pages):
    paginator = MagicMock()
    paginator.paginate.return_value = [{"AutoScalingGroups": asgs} for asgs in pages]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    return client


class TestLog:
    def test_info_writes_to_stdout(self, capsys):
        _log("INFO", "hello", "start")
        captured = capsys.readouterr()
        assert captured.err == ""
        data = json.loads(captured.out.strip())
        assert data["level"] == "INFO"
        assert data["message"] == "hello"
        assert data["command"] == "start"

    def test_error_writes_to_stderr(self, capsys):
        _log("ERROR", "bad", "monitor")
        captured = capsys.readouterr()
        assert captured.out == ""
        data = json.loads(captured.err.strip())
        assert data["level"] == "ERROR"
        assert data["message"] == "bad"
        assert data["command"] == "monitor"


class TestLookupAsg:
    def test_zero_matches_exits_1(self):
        client = _make_client([[]])
        with pytest.raises(SystemExit) as exc:
            lookup_asg(client, "Name", "my-asg", "start")
        assert exc.value.code == 1

    def test_multiple_matches_exits_1(self):
        client = _make_client(
            [
                [
                    _make_asg("asg-1", {"Name": "my-asg"}),
                    _make_asg("asg-2", {"Name": "my-asg"}),
                ]
            ]
        )
        with pytest.raises(SystemExit) as exc:
            lookup_asg(client, "Name", "my-asg", "start")
        assert exc.value.code == 1

    def test_single_match_returns_name(self):
        client = _make_client([[_make_asg("target", {"Name": "my-asg"})]])
        assert lookup_asg(client, "Name", "my-asg", "start") == "target"

    def test_pagination_two_pages(self):
        client = _make_client(
            [
                [_make_asg("other", {"Env": "prod"})],
                [_make_asg("target", {"Name": "my-asg"})],
            ]
        )
        assert lookup_asg(client, "Name", "my-asg", "start") == "target"

    def test_case_sensitive_tag_value(self):
        client = _make_client([[_make_asg("asg", {"Name": "MY-ASG"})]])
        with pytest.raises(SystemExit) as exc:
            lookup_asg(client, "Name", "my-asg", "start")
        assert exc.value.code == 1

    def test_case_sensitive_tag_key(self):
        client = _make_client([[_make_asg("asg", {"name": "my-asg"})]])
        with pytest.raises(SystemExit) as exc:
            lookup_asg(client, "Name", "my-asg", "start")
        assert exc.value.code == 1
