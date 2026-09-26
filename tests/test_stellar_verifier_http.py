"""HTTP-path tests for ``stellar_verifier`` (Wave 9 / DripsLens #6).

The existing coverage exercises the address-shape helpers and the ``None`` /
invalid-id branches of ``verify_account``. The two functions that actually talk
to the network — ``_check_horizon`` and ``_check_contract`` — were never
called, so a parsing bug there would silently corrupt ``repo.stellar_verified``
for every repo.

Everything below mocks the transport, so no test touches the network:

* ``httpx.get`` / ``httpx.post`` are patched on the module, which is where
  ``stellar_verifier`` looks them up.
* ``settings.stellar_rpc_url`` is patched per-test; it is read inside
  ``_check_contract`` rather than captured at import time.
"""

import httpx
import pytest

from app.config import settings
from app.scrapers import stellar_verifier
from app.scrapers.stellar_verifier import (
    _check_contract,
    _check_horizon,
    verify_account,
)

ACCOUNT = "G" + "A" * 55
CONTRACT = "C" + "A" * 55


# --- fixtures ---------------------------------------------------------------


@pytest.fixture()
def horizon_calls(monkeypatch):
    """Record every Horizon GET and answer with whatever the test queues up.

    Yields a list of requested URLs; the response is taken from ``queue``, a
    one-item list the test fills in.
    """
    queue: list = []
    seen: list[str] = []

    def fake_get(url, **_kwargs):
        seen.append(url)
        if not queue:
            raise AssertionError(f"unexpected Horizon call to {url}")
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(stellar_verifier.httpx, "get", fake_get)
    return {"seen": seen, "queue": queue}


@pytest.fixture()
def rpc_calls(monkeypatch):
    """Record every Soroban POST and answer with whatever the test queues up."""
    queue: list = []
    seen: list = []

    def fake_post(url, **_kwargs):
        seen.append(url)
        if not queue:
            raise AssertionError(f"unexpected Soroban call to {url}")
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(stellar_verifier.httpx, "post", fake_post)
    return {"seen": seen, "queue": queue}


def horizon_ok(balances=None):
    """A 200 response in the shape Horizon returns."""
    return httpx.Response(
        200,
        json={"account_id": ACCOUNT, "balances": balances if balances is not None else []},
    )


def rpc_response(status_code: int, *, json_body=None, text: str | None = None):
    """A response that can survive ``raise_for_status()``.

    ``_check_contract`` calls ``resp.raise_for_status()``, and httpx refuses
    that on a response with no request attached (``RuntimeError: Cannot call
    raise_for_status as the request instance has not been set``). Binding a
    request makes the helper behave like a real transport response.

    Note this is a wrinkle the issue's suggested recipe
    (``httpx.Response(status_code, ...)``) does not cover — it only surfaces on
    the paths that call ``raise_for_status``.
    """
    request = httpx.Request("POST", "https://rpc.example.test")
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=request)
    return httpx.Response(status_code, text=text or "", request=request)


def rpc_ok(entries):
    """A Soroban getLedgerEntries response with the given entries."""
    return rpc_response(200, json_body={"jsonrpc": "2.0", "id": 1, "result": {"entries": entries}})


# --- _check_horizon ---------------------------------------------------------


def test_check_horizon_200_is_verified(horizon_calls):
    horizon_calls["queue"].append(
        horizon_ok([{"asset_type": "native", "balance": "42.5000000"}])
    )

    result = _check_horizon(ACCOUNT)

    assert result.status == "verified"
    assert result.account_or_contract == ACCOUNT


def test_check_horizon_surfaces_xlm_balance_in_detail(horizon_calls):
    horizon_calls["queue"].append(
        horizon_ok(
            [
                {"asset_type": "credit_alphanum4", "balance": "10.0", "asset_code": "USDC"},
                {"asset_type": "native", "balance": "123.4567890"},
            ]
        )
    )

    result = _check_horizon(ACCOUNT)

    assert result.status == "verified"
    assert result.detail is not None
    assert "123.4567890" in result.detail


def test_check_horizon_200_without_native_balance_still_verified(horizon_calls):
    """A funded account always has a native balance, but the code must not
    crash if Horizon omits it — the balance is decoration on the detail string.
    """
    horizon_calls["queue"].append(
        horizon_ok([{"asset_type": "credit_alphanum4", "balance": "5.0"}])
    )

    result = _check_horizon(ACCOUNT)

    assert result.status == "verified"
    assert result.detail == "account exists on Horizon"


def test_check_horizon_404_is_unverified(horizon_calls):
    horizon_calls["queue"].append(httpx.Response(404, json={"status": 404}))

    result = _check_horizon(ACCOUNT)

    assert result.status == "unverified"
    assert result.detail is not None
    assert "no such account" in result.detail.lower()


def test_check_horizon_500_is_unknown(horizon_calls):
    horizon_calls["queue"].append(httpx.Response(500, text="boom"))

    result = _check_horizon(ACCOUNT)

    assert result.status == "unknown"
    assert result.detail is not None
    assert "500" in result.detail


def test_check_horizon_429_is_unknown_not_unverified(horizon_calls):
    """Rate limiting must not be read as "this account does not exist"."""
    horizon_calls["queue"].append(httpx.Response(429, text="slow down"))

    result = _check_horizon(ACCOUNT)

    assert result.status == "unknown"
    assert result.status != "unverified"


def test_check_horizon_connect_error_is_unknown(horizon_calls):
    horizon_calls["queue"].append(httpx.ConnectError("connection refused"))

    result = _check_horizon(ACCOUNT)

    assert result.status == "unknown"
    assert result.detail is not None
    assert "connection refused" in result.detail


def test_check_horizon_timeout_is_unknown(horizon_calls):
    horizon_calls["queue"].append(httpx.TimeoutException("timed out"))

    result = _check_horizon(ACCOUNT)

    assert result.status == "unknown"


def test_check_horizon_requests_the_account_path(horizon_calls):
    horizon_calls["queue"].append(horizon_ok())

    _check_horizon(ACCOUNT)

    assert len(horizon_calls["seen"]) == 1
    assert horizon_calls["seen"][0].endswith(f"/accounts/{ACCOUNT}")
    assert horizon_calls["seen"][0].startswith(settings.stellar_horizon_url.rstrip("/"))


# --- _check_contract --------------------------------------------------------


def test_check_contract_without_rpc_url_is_unknown(monkeypatch, rpc_calls):
    monkeypatch.setattr(settings, "stellar_rpc_url", "")

    result = _check_contract(CONTRACT)

    assert result.status == "unknown"
    assert result.detail is not None
    # The detail must say why, so an operator knows to configure the URL.
    assert "STELLAR_RPC_URL" in result.detail
    # And it must not have made a request at all.
    assert rpc_calls["seen"] == []


def test_check_contract_with_entries_is_verified(monkeypatch, rpc_calls):
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://rpc.example.test")
    rpc_calls["queue"].append(rpc_ok([{"key": "abc", "xdr": "AAAA"}]))

    result = _check_contract(CONTRACT)

    assert result.status == "verified"
    assert result.account_or_contract == CONTRACT
    assert rpc_calls["seen"] == ["https://rpc.example.test"]


def test_check_contract_with_empty_entries_is_unverified(monkeypatch, rpc_calls):
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://rpc.example.test")
    rpc_calls["queue"].append(rpc_ok([]))

    result = _check_contract(CONTRACT)

    assert result.status == "unverified"


def test_check_contract_http_error_is_unknown(monkeypatch, rpc_calls):
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://rpc.example.test")
    rpc_calls["queue"].append(httpx.ConnectError("unreachable"))

    result = _check_contract(CONTRACT)

    assert result.status == "unknown"
    assert result.detail is not None


def test_check_contract_server_error_is_unknown(monkeypatch, rpc_calls):
    """raise_for_status() turns a 5xx into an HTTPStatusError."""
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://rpc.example.test")
    rpc_calls["queue"].append(rpc_response(503, json_body={"error": "unavailable"}))

    result = _check_contract(CONTRACT)

    assert result.status == "unknown"


def test_check_contract_invalid_json_is_unknown(monkeypatch, rpc_calls):
    """A non-JSON body raises ValueError on .json(), which is caught."""
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://rpc.example.test")
    rpc_calls["queue"].append(rpc_response(200, text="<html>not json</html>"))

    result = _check_contract(CONTRACT)

    assert result.status == "unknown"


# --- verify_account routing -------------------------------------------------


def test_verify_account_routes_g_to_horizon(monkeypatch):
    """A G... id must go to Horizon and must not touch Soroban."""
    called = {}

    def fake_horizon(account_id):
        called["horizon"] = account_id
        return stellar_verifier.VerificationResult(account_id, "verified")

    def fake_contract(contract_id):  # pragma: no cover - must not be reached
        called["contract"] = contract_id
        raise AssertionError("a G... id must not be routed to the Soroban path")

    monkeypatch.setattr(stellar_verifier, "_check_horizon", fake_horizon)
    monkeypatch.setattr(stellar_verifier, "_check_contract", fake_contract)

    result = verify_account(ACCOUNT)

    assert result.status == "verified"
    assert called == {"horizon": ACCOUNT}


def test_verify_account_routes_c_to_soroban(monkeypatch):
    """A C... id must go to Soroban and must not touch Horizon."""
    called = {}

    def fake_contract(contract_id):
        called["contract"] = contract_id
        return stellar_verifier.VerificationResult(contract_id, "verified")

    def fake_horizon(account_id):  # pragma: no cover - must not be reached
        called["horizon"] = account_id
        raise AssertionError("a C... id must not be routed to the Horizon path")

    monkeypatch.setattr(stellar_verifier, "_check_horizon", fake_horizon)
    monkeypatch.setattr(stellar_verifier, "_check_contract", fake_contract)

    result = verify_account(CONTRACT)

    assert result.status == "verified"
    assert called == {"contract": CONTRACT}


def test_verify_account_routing_through_mocked_transport(horizon_calls, rpc_calls, monkeypatch):
    """End-to-end through verify_account with only the transport mocked.

    This is the path ``refresh_repos`` takes, so it is the one whose result is
    written to ``repo.stellar_verified``.
    """
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://rpc.example.test")

    horizon_calls["queue"].append(horizon_ok([{"asset_type": "native", "balance": "1.0"}]))
    rpc_calls["queue"].append(rpc_ok([{"key": "k", "xdr": "x"}]))

    account_result = verify_account(ACCOUNT)
    contract_result = verify_account(CONTRACT)

    assert account_result.status == "verified"
    assert contract_result.status == "verified"
    assert len(horizon_calls["seen"]) == 1
    assert len(rpc_calls["seen"]) == 1
