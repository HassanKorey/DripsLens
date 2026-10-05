import httpx
import os

STELLAR_HORIZON_URL = os.getenv("STELLAR_HORIZON_URL", "https://horizon-testnet.stellar.org")

async def verify_stellar_account(account_id: str) -> bool:
    # Verifies discovered public keys against Stellar Horizon API
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{STELLAR_HORIZON_URL}/accounts/{account_id}")
        return response.status_code == 200
