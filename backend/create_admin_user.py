#!/usr/bin/env python3
"""Create an admin user for development/testing."""

import asyncio
import uuid_utils
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import select, text

from yourai.core.config import settings
from yourai.core.models import Tenant, User, Role, Permission, UserRole, RolePermission
from yourai.core.enums import UserStatus
from yourai.core.auth import AuthService


async def main():
    """Create admin user and print JWT token."""

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # 1. Check if tenant exists, create if not
        result = await session.execute(
            select(Tenant).where(Tenant.slug == "demo-tenant")
        )
        tenant = result.scalar_one_or_none()

        if tenant is None:
            print("Creating tenant...")
            # Use raw SQL to avoid type issues
            await session.execute(
                text("""
                    INSERT INTO tenants (id, name, slug, industry_vertical, branding_config, 
                                       subscription_tier, is_active, news_feed_urls, 
                                       external_source_integrations, ai_config)
                    VALUES (:id, :name, :slug, :industry_vertical, :branding_config::jsonb,
                           'starter'::subscription_tier, true, '[]'::jsonb, '[]'::jsonb, '{}'::jsonb)
                """),
                {
                    "id": str(uuid_utils.uuid7()),
                    "name": "Demo Tenant",
                    "slug": "demo-tenant",
                    "industry_vertical": "financial_services",
                    "branding_config": '{"logo_url": "", "primary_color": "#1a73e8", "name": "Demo Tenant"}',
                }
            )
            await session.flush()
            
            # Reload tenant
            result = await session.execute(
                select(Tenant).where(Tenant.slug == "demo-tenant")
            )
            tenant = result.scalar_one()
            print(f"✅ Created tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"✅ Using existing tenant: {tenant.name} (ID: {tenant.id})")

        # 2. Create admin role
        result = await session.execute(
            select(Role).where(
                Role.tenant_id == tenant.id,
                Role.name == "Admin"
            )
        )
        admin_role = result.scalar_one_or_none()

        if admin_role is None:
            print("Creating admin role...")
            admin_role = Role(
                id=uuid_utils.uuid7(),
                tenant_id=tenant.id,
                name="Admin",
                description="Full system access",
            )
            session.add(admin_role)
            await session.flush()

            # Create permissions
            permission_names = [
                "list_users", "create_user", "update_user", "delete_user",
                "list_roles", "create_role", "update_role", "delete_role",
                "list_knowledge_bases", "create_knowledge_base", "update_knowledge_base", "delete_knowledge_base",
                "upload_document", "delete_document",
                "start_policy_review", "view_policy_review",
                "list_conversations", "send_message",
            ]

            for perm_name in permission_names:
                result = await session.execute(
                    select(Permission).where(Permission.name == perm_name)
                )
                permission = result.scalar_one_or_none()

                if permission is None:
                    permission = Permission(
                        id=uuid_utils.uuid7(),
                        name=perm_name,
                        description=f"Permission: {perm_name}",
                    )
                    session.add(permission)
                    await session.flush()

                session.add(RolePermission(
                    role_id=admin_role.id,
                    permission_id=permission.id
                ))

            await session.flush()
            print(f"✅ Created admin role with {len(permission_names)} permissions")
        else:
            print(f"✅ Using existing admin role")

        # 3. Create admin user
        admin_email = "admin@demo.test"
        result = await session.execute(
            select(User).where(
                User.tenant_id == tenant.id,
                User.email == admin_email
            )
        )
        admin_user = result.scalar_one_or_none()

        if admin_user is None:
            print("Creating admin user...")
            admin_user = User(
                id=uuid_utils.uuid7(),
                tenant_id=tenant.id,
                email=admin_email,
                given_name="Admin",
                family_name="User",
                job_role="Administrator",
                status=UserStatus.ACTIVE,
                notification_preferences={},
            )
            session.add(admin_user)
            await session.flush()

            session.add(UserRole(
                user_id=admin_user.id,
                role_id=admin_role.id
            ))
            await session.flush()
            print(f"✅ Created admin user: {admin_user.email}")
        else:
            print(f"✅ Using existing admin user: {admin_user.email}")

        await session.commit()

        # 4. Generate JWT token
        auth_service = AuthService()
        token = auth_service.create_access_token(
            user_id=admin_user.id,
            tenant_id=tenant.id,
            email=admin_user.email,
        )

        print("\n" + "="*80)
        print("ADMIN USER CREATED SUCCESSFULLY")
        print("="*80)
        print(f"Email:     {admin_user.email}")
        print(f"Name:      {admin_user.given_name} {admin_user.family_name}")
        print(f"Tenant:    {tenant.name}")
        print(f"Role:      Admin")
        print("\n" + "-"*80)
        print("JWT TOKEN (expires in 60 minutes):")
        print("-"*80)
        print(token)
        print("\n" + "="*80)
        print("\nTO USE THIS TOKEN IN THE FRONTEND:")
        print("1. Go to http://localhost:3000")
        print("2. Open DevTools (F12) > Application > Local Storage")
        print("3. Add:")
        print("   Key:   yourai_token")
        print(f"   Value: {token}")
        print("4. Refresh the page")
        print("\nOR USE IN API CALLS:")
        print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/users')
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
