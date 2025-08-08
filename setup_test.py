import json
from unittest.mock import patch, MagicMock

import setup as setup_mod


def test_is_address_valid_and_invalid():
    assert setup_mod.is_address("0x" + "a" * 40)
    assert not setup_mod.is_address("0x123")
    assert not setup_mod.is_address("notanaddress")


def test_fetch_router_abi_success_with_key():
    good_payload = {"status": "1", "result": json.dumps([{"type": "function", "name": "foo"}])}
    mock_resp = MagicMock()
    mock_resp.json.return_value = good_payload
    mock_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_resp) as mock_get:
        abi = setup_mod.fetch_router_abi("0x" + "1" * 40, api_key="abc")
        assert isinstance(abi, list)
        assert abi[0]["name"] == "foo"
        mock_get.assert_called_once()
        called_params = mock_get.call_args.kwargs["params"]
        assert called_params["module"] == "contract"
        assert called_params["action"] == "getabi"
        assert called_params["apikey"] == "abc"


def test_fetch_router_abi_handles_error_payload():
    bad_payload = {"status": "0", "result": "error"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = bad_payload
    mock_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_resp):
        abi = setup_mod.fetch_router_abi("0x" + "2" * 40, api_key=None)
        assert abi is None


def test_write_env(tmp_path):
    env_path = tmp_path / ".env"
    setup_mod.write_env(str(env_path), {"A": "1", "B": "two"})
    content = env_path.read_text()
    assert "A=1" in content
    assert "B=two" in content


def test_prompt_default_non_secret(monkeypatch):
    inputs = iter([""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    out = setup_mod.prompt("Enter something", default="def")
    assert out == "def"