import requests

def verify_stellar_account(account_id_or_contract: str):
    # Check Horizon API for account existence
    # Returns True if exists, False otherwise
    try:
        response = requests.get(f"https://horizon.stellar.org/accounts/{account_id_or_contract}")
        if response.status_code == 200:
            return True
    except Exception:
        pass
    return False
