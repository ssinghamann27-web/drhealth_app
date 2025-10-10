# -*- coding: utf-8 -*-
"""
Traffic Test Script 🚦
Generates load against FastAPI to visualize metrics in Grafana.
"""

import sys
import asyncio
import aiohttp
import time

# ✅ Fix Windows PowerShell encoding
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 🔹 Your FastAPI base URL
API_URL = "http://localhost:8000"

# 🔹 Load Settings
REQUESTS_PER_SECOND = 50   # 🔸 how many requests per second
DURATION_SECONDS = 20       # 🔸 how long to run test (seconds)
ENDPOINT = "/docs"          # 🔸 endpoint to hit (can change)

async def hit_endpoint(session, endpoint=ENDPOINT):
    """Hit a single endpoint and return status code"""
    url = f"{API_URL}{endpoint}"
    try:
        async with session.get(url) as response:
            await response.text()
            return response.status
    except Exception as e:
        return f"Error: {str(e)}"

async def main():
    """Main loop to send traffic"""
    start = time.time()
    print(f"\n🚀 Starting traffic test → {API_URL}{ENDPOINT}")
    print(f"⏱  Duration: {DURATION_SECONDS}s | ⚡ RPS: {REQUESTS_PER_SECOND}\n")

    async with aiohttp.ClientSession() as session:
        while time.time() - start < DURATION_SECONDS:
            # Create multiple async requests per second
            tasks = [hit_endpoint(session) for _ in range(REQUESTS_PER_SECOND)]
            results = await asyncio.gather(*tasks)

            # Aggregate results
            success = sum(1 for r in results if r == 200)
            errors = len(results) - success
            print(f"✅ OK: {success:3} | ❌ Errors: {errors:3}")
            await asyncio.sleep(1)

    print("\n🏁 Load test completed. Check Grafana for metrics!")

if __name__ == "__main__":
    asyncio.run(main())
