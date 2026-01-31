import asyncio
import os
import httpx
from config import get_env

async def test_auth():
    print("--- Debugging Product Hunt Auth ---")
    
    key = get_env("PRODUCTHUNT_API_KEY")
    secret = get_env("PRODUCTHUNT_API_SECRET")
    
    print(f"Key loaded: {bool(key)}")
    print(f"Secret loaded: {bool(secret)}")
    
    if not key or not secret:
        print("❌ Missing credentials in .env")
        return

    async with httpx.AsyncClient() as client:
        # Auth
        try:
            resp = await client.post(
                "https://api.producthunt.com/v2/oauth/token",
                json={
                    "client_id": key,
                    "client_secret": secret,
                    "grant_type": "client_credentials",
                }
            )
            print(f"Auth Status: {resp.status_code}")
            if resp.status_code == 200:
                print("✅ Auth Success")
                token = resp.json().get("access_token")
                
                # Test Query
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                query = """
                query {
                    posts(first: 1) {
                        edges { node { name } }
                    }
                }
                """
                
                q_resp = await client.post(
                    "https://api.producthunt.com/v2/api/graphql",
                    headers=headers,
                    json={"query": query}
                )
                print(f"Query Status: {q_resp.status_code}")
                print(f"Query Body: {q_resp.text[:200]}")
                
            else:
                print(f"❌ Auth Failed: {resp.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
