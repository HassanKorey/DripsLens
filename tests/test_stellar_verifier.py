"""Unit tests for stellar_verifier HTTP paths (Horizon + Soroban RPC)."""

import httpx

from app.config import settings
from app.scrapers import stellar_verifier
from app.scrapers.stellar_verifier import (
    _check_contract,
    _check_horizon,
    verify_account,
)


def test_check_horizon_200_verified_with_xlm(monkeypatch):
    account_id = "G" + "A" * 55

    def fake_get(url, timeout=None, headers=None):
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={
                "balances": [
                    {"asset_type": "credit_alphanum4", "balance": "100.0"},
                    {"asset_type": "native", "balance": "42.5000000"},
                ]
            },
        )

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.get", fake_get)
    result = _check_horizon(account_id)

    assert result.account_or_contract == account_id
    assert result.status == "verified"
    assert result.detail is not None
    assert "account exists on Horizon" in result.detail
    assert "XLM balance 42.5000000" in result.detail


def test_check_horizon_200_verified_without_xlm(monkeypatch):
    account_id = "G" + "A" * 55

    def fake_get(url, timeout=None, headers=None):
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req, json={"balances": []})

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.get", fake_get)
    result = _check_horizon(account_id)

    assert result.account_or_contract == account_id
    assert result.status == "verified"
    assert result.detail == "account exists on Horizon"


def test_check_horizon_404_unverified(monkeypatch):
    account_id = "G" + "A" * 55

    def fake_get(url, timeout=None, headers=None):
        req = httpx.Request("GET", url)
        return httpx.Response(404, request=req, json={"detail": "Not found"})

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.get", fake_get)
    result = _check_horizon(account_id)

    assert result.account_or_contract == account_id
    assert result.status == "unverified"
    assert result.detail == "no such account on Horizon"


def test_check_horizon_500_unknown(monkeypatch):
    account_id = "G" + "A" * 55

    def fake_get(url, timeout=None, headers=None):
        req = httpx.Request("GET", url)
        return httpx.Response(500, request=req, json={"detail": "Server error"})

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.get", fake_get)
    result = _check_horizon(account_id)

    assert result.account_or_contract == account_id
    assert result.status == "unknown"
    assert result.detail == "Horizon returned 500"


def test_check_horizon_connect_error_unknown(monkeypatch):
    account_id = "G" + "A" * 55

    def fake_get(url, timeout=None, headers=None):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.get", fake_get)
    result = _check_horizon(account_id)

    assert result.account_or_contract == account_id
    assert result.status == "unknown"
    assert result.detail == "boom"


def test_check_contract_no_rpc_url_configured(monkeypatch):
    contract_id = "C" + "A" * 55
    monkeypatch.setattr(settings, "stellar_rpc_url", "")

    result = _check_contract(contract_id)

    assert result.account_or_contract == contract_id
    assert result.status == "unknown"
    assert result.detail == "STELLAR_RPC_URL not configured; cannot verify contracts"


def test_check_contract_rpc_entries_verified(monkeypatch):
    contract_id = "C" + "A" * 55
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://soroban-testnet.stellar.org")

    def fake_post(url, json=None, timeout=None):
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=req,
            json={"jsonrpc": "2.0", "result": {"entries": [{"key": "instance_key"}]}},
        )

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.post", fake_post)
    result = _check_contract(contract_id)

    assert result.account_or_contract == contract_id
    assert result.status == "verified"
    assert result.detail == "contract instance found on ledger"


def test_check_contract_rpc_empty_entries_unverified(monkeypatch):
    contract_id = "C" + "A" * 55
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://soroban-testnet.stellar.org")

    def fake_post(url, json=None, timeout=None):
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=req,
            json={"jsonrpc": "2.0", "result": {"entries": []}},
        )

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.post", fake_post)
    result = _check_contract(contract_id)

    assert result.account_or_contract == contract_id
    assert result.status == "unverified"
    assert result.detail == "no contract instance on ledger"


def test_check_contract_rpc_http_error_unknown(monkeypatch):
    contract_id = "C" + "A" * 55
    monkeypatch.setattr(settings, "stellar_rpc_url", "https://soroban-testnet.stellar.org")

    def fake_post(url, json=None, timeout=None):
        raise httpx.ConnectError("rpc unreachable")

    monkeypatch.setattr("app.scrapers.stellar_verifier.httpx.post", fake_post)
    result = _check_contract(contract_id)

    assert result.account_or_contract == contract_id
    assert result.status == "unknown"
    assert result.detail == "rpc unreachable"


def test_verify_account_routing(monkeypatch):
    account_id = "G" + "A" * 55
    contract_id = "C" + "A" * 55

    monkeypatch.setattr(
        stellar_verifier,
        "_check_horizon",
        lambda acct: stellar_verifier.VerificationResult(acct, "verified", "horizon_mock"),
    )
    monkeypatch.setattr(
        stellar_verifier,
        "_check_contract",
        lambda cid: stellar_verifier.VerificationResult(cid, "verified", "contract_mock"),
    )

    res_account = verify_account(account_id)
    assert res_account.detail == "horizon_mock"

    res_contract = verify_account(contract_id)
    assert res_contract.detail == "contract_mock"
