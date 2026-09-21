import httpx

from .config import settings


def list_dataset_assets(dataset_id: str) -> list[dict]:
    page_size = 500
    offset = 0
    all_assets: list[dict] = []
    while True:
        resp = httpx.get(
            f"{settings.dataset_service_url}/api/dataset/{dataset_id}/assets",
            params={"limit": page_size, "offset": offset},
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()
        all_assets.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_assets


def get_dataset(dataset_id: str) -> dict:
    resp = httpx.get(f"{settings.dataset_service_url}/api/dataset/{dataset_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_asset(asset_id: str) -> dict:
    resp = httpx.get(f"{settings.dataset_service_url}/api/dataset/assets/{asset_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()
