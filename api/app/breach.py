import httpx

from .analyzer import sha1_prefix


async def check_hibp(password: str) -> tuple[bool, int]:
    prefix, suffix = sha1_prefix(password)
    async with httpx.AsyncClient(
        base_url="https://api.pwnedpasswords.com",
        timeout=8.0,
        headers={"Add-Padding": "true", "User-Agent": "SecureScope/0.1"},
    ) as client:
        response = await client.get(f"/range/{prefix}")
        response.raise_for_status()

    for line in response.text.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.upper() == suffix:
            return True, int(count)
    return False, 0
