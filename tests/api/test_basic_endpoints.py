import os
import pytest
import httpx

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.mark.asyncio
async def test_health_like_endpoints():
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(f"{API_BASE}/admin/index")
        assert r.status_code in (200, 401, 403)

@pytest.mark.asyncio
async def test_settings_get():
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(f"{API_BASE}/admin/settings")
        assert r.status_code in (200, 401, 403)

