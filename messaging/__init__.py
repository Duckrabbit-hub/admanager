from config import get_account

from .base import MessagingConnector
from .facebook_messenger import FacebookMessengerConnector
from .shopee_chat import ShopeeChatConnector

_CONNECTOR_CLASSES = {
    "facebook": FacebookMessengerConnector,
    "shopee": ShopeeChatConnector,
}

MESSAGING_PLATFORMS = list(_CONNECTOR_CLASSES.keys())


def get_messaging_connector(platform, account_id=None):
    cls = _CONNECTOR_CLASSES.get(platform, MessagingConnector)
    account = get_account(platform, account_id) if account_id else None
    return cls(account)
