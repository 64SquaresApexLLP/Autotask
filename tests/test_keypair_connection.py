#!/usr/bin/env python3
"""
Verify Snowflake key-pair (RSA) authentication works without a password / TOTP.

Before running, make sure the RSA public key is registered on the Snowflake user:
    ALTER USER ATISHC SET RSA_PUBLIC_KEY='<base64 body of rsa_key.pub>';

Run from the project root:
    python tests/test_keypair_connection.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_keypair_connection():
    """Connect using key-pair auth and run a sanity query."""
    from src.database.snowflake_db import SnowflakeConnection
    from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA,
                        SF_ROLE, SF_AUTHENTICATOR, SF_PASSWORD,
                        SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

    print("🔑 Testing Snowflake Key-Pair Connection...")
    print(f"   Account:        {SF_ACCOUNT}")
    print(f"   User:           {SF_USER}")
    print(f"   Authenticator:  {SF_AUTHENTICATOR}")
    print(f"   Private key:    {SF_PRIVATE_KEY_PATH}")
    print(f"   Password used:  {'YES (should be blank for key-pair)' if SF_PASSWORD else 'no'}")
    print("-" * 60)

    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT,
        sf_user=SF_USER,
        sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE,
        sf_schema=SF_SCHEMA,
        sf_role=SF_ROLE,
        sf_password=SF_PASSWORD,
        sf_authenticator=SF_AUTHENTICATOR,
        sf_private_key_file=SF_PRIVATE_KEY_PATH,
        sf_private_key_pwd=SF_PRIVATE_KEY_PWD,
    )

    if not conn.is_connected():
        print("❌ Key-pair connection failed!")
        return False

    result = conn.execute_query("SELECT CURRENT_USER() AS U, CURRENT_ROLE() AS R, CURRENT_WAREHOUSE() AS W")
    if result:
        row = result[0]
        print(f"✅ Connected as: {row.get('U')}")
        print(f"   Role:       {row.get('R')}")
        print(f"   Warehouse:  {row.get('W')}")
    else:
        print("❌ Verification query returned no rows!")
        conn.close_connection()
        return False

    conn.close_connection()
    print("\n🎉 Key-pair authentication works — no password, no TOTP/MFA needed.")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_keypair_connection() else 1)