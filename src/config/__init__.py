from config.settings import BaseAppSettings
from config.dependencies import (
    get_settings,
    get_jwt_auth_manager,
    get_accounts_email_notificator,
    get_s3_storage_client
)
from config.order_config import (
    create_order_service,
    check_pending_orders,
    get_purchased_movie_ids
)
