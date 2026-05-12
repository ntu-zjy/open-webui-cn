"""Seed a local-only super admin with Pro subscription for development.

Run after `alembic upgrade head` and `seed_plans`:
    python -m scripts.seed_dev_admin

Idempotent — re-running upgrades the existing account back to admin + extends Pro.
NEVER deploy this to production.
"""
import asyncio
import sys

sys.path.insert(0, 'backend')

from open_webui.internal.db import get_async_db_context  # noqa: E402
from open_webui.models.auths import Auths  # noqa: E402
from open_webui.models.users import Users, User  # noqa: E402
from open_webui.models.subscriptions import Subscriptions  # noqa: E402
from open_webui.utils.auth import get_password_hash  # noqa: E402


EMAIL = 'admin@local.dev'
PASSWORD = 'admin1234'
NAME = 'Local Admin'
ONE_YEAR = 365 * 24 * 3600


async def main() -> None:
    existing = await Users.get_user_by_email(EMAIL)

    import secrets
    avatar = f'/static/avatars/{secrets.randbelow(8) + 1}.svg'

    if existing is None:
        user = await Auths.insert_new_auth(
            email=EMAIL,
            password=get_password_hash(PASSWORD),
            name=NAME,
            profile_image_url=avatar,
            role='admin',
        )
        if user is None:
            print('FAILED to create admin')
            return
        user_id = user.id
        print(f'created admin user {user_id}')
    else:
        user_id = existing.id
        async with get_async_db_context() as db:
            row = await db.get(User, user_id)
            row.role = 'admin'
            if row.profile_image_url in ('/user.png', '', None):
                row.profile_image_url = avatar
            await db.commit()
        print(f'upgraded existing user {user_id} to admin')

    sub = await Subscriptions.grant_or_extend(
        user_id=user_id, plan_code='pro', seconds=ONE_YEAR,
    )
    print(f'granted Pro until {sub.expires_at}')
    print()
    print(f'  email:    {EMAIL}')
    print(f'  password: {PASSWORD}')


if __name__ == '__main__':
    asyncio.run(main())
