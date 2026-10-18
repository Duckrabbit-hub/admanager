from config import get_account

from .base import AdConnector
from .facebook_ads import FacebookAdsConnector
from .tiktok_ads import TikTokAdsConnector
from .shopee_ads import ShopeeAdsConnector

_CONNECTOR_CLASSES = {
    "facebook": FacebookAdsConnector,
    "tiktok": TikTokAdsConnector,
    "shopee": ShopeeAdsConnector,
}


def get_connector(platform, account_id=None):
    cls = _CONNECTOR_CLASSES.get(platform, AdConnector)
    account = get_account(platform, account_id) if account_id else None
    return cls(account)
