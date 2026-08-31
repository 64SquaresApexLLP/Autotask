#!/usr/bin/env python3
"""
One-time setup for Snowflake key-pair (RSA) authentication.

This removes the need for a password / TOTP (MFA) passcode for the Snowflake
service account used by this app. It performs three things:

  1. Generates an RSA key pair (rsa_key.p8 / rsa_key.pub) if it does not exist:
       openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
       openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

  2. Prints the ALTER USER statement needed to register the public key on Snowflake:
       ALTER USER ATISHC SET RSA_PUBLIC_KEY='<base64 body of rsa_key.pub>';

  3. With --register, connects with the credentials currently in .env and runs
     that ALTER USER for you (this step may still trigger MFA ONCE — that is the
     last time you will need it, because the app then authenticates with the key).

  4. Tests that the app's key-pair connection works (no password, no TOTP).

Usage:
    python scripts/setup_keypair_auth.py                 # generate keys + print ALTER USER
    python scripts/setup_keypair_auth.py --register      # also register the pubkey on Snowflake
    python scripts/setup_keypair_auth.py --test          # only test the key-pair connection
"""

import argparse
import os
import subprocess
import sys

# Ensure the Autotask root is importable so `config` and `src.database` resolve.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def generate_key_pair(key_path: str, pub_path: str, force: bool = False) -> None:
    """Generate rsa_key.p8 + rsa_key.pub (skips if they already exist unless --force)."""
    if os.path.exists(key_path) and os.path.exists(pub_path) and not force:
        print(f"[OK] Key pair already exists: {key_path} / {pub_path}")
        return

    pem = subprocess.run(
        ['openssl', 'genrsa', '2048'],
        check=True, capture_output=True
    )
    pkcs8 = subprocess.run(
        ['openssl', 'pkcs8', '-topk8', '-inform', 'PEM', '-nocrypt'],
        input=pem.stdout, check=True, capture_output=True
    )
    with open(key_path, 'wb') as f:
        f.write(pkcs8.stdout)
    os.chmod(key_path, 0o600)
    print(f"[OK] Private key written: {key_path} (mode 0600)")

    pub = subprocess.run(
        ['openssl', 'rsa', '-in', key_path, '-pubout'],
        check=True, capture_output=True
    )
    with open(pub_path, 'wb') as f:
        f.write(pub.stdout)
    print(f"[OK] Public key written:  {pub_path}")


def read_pubkey_body(pub_path: str) -> str:
    """Return the base64 body of the PEM public key (everything inside the -- markers)."""
    with open(pub_path, 'r') as f:
        lines = f.read().strip().splitlines()
    return ''.join(
        line.strip() for line in lines
        if '-----BEGIN' not in line and '-----END' not in line
    )


def register_public_key(user: str, pub_body: str) -> bool:
    """Connect using the current .env credentials and register the public key."""
    import config

    if not config.SF_PASSWORD:
        print("[ERROR] SF_PASSWORD is commented out in .env. For the ONE-TIME registration step you still need "
              "password credentials (MFA may be prompted). Uncomment SF_PASSWORD in .env and re-run with --register.")
        return False

    from src.database.snowflake_db import SnowflakeConnection

    print("\n[*] Registering RSA public key using account credentials (one-time, may prompt MFA)...")
    conn = SnowflakeConnection(
        sf_account=config.SF_ACCOUNT,
        sf_user=config.SF_USER,
        sf_warehouse=config.SF_WAREHOUSE,
        sf_database=config.SF_DATABASE,
        sf_schema=config.SF_SCHEMA,
        sf_role=config.SF_ROLE,
        sf_authenticator='snowflake',          # force password auth for this one-time step
        sf_password=config.SF_PASSWORD,
        sf_passcode=config.SF_PASSCODE,
    )
    if not conn.is_connected():
        print("[ERROR] Could not connect to Snowflake for registration.")
        return False

    alter_sql = f"ALTER USER {config.SF_USER} SET RSA_PUBLIC_KEY='{pub_body}';"
    try:
        conn.execute_query(alter_sql)
        print(f"[OK] RSA public key registered for user {config.SF_USER}.")
        return True
    except Exception as e:
        print(f"[ERROR] ALTER USER failed: {e}")
        return False
    finally:
        conn.close_connection()


def test_keypair_connection() -> bool:
    """Test the key-pair connection exactly as the app uses it."""
    import config

    print("\n[*] Testing key-pair connection (RSA key only — no password, no TOTP)...")
    from src.database.snowflake_db import SnowflakeConnection

    conn = SnowflakeConnection(
        sf_account=config.SF_ACCOUNT,
        sf_user=config.SF_USER,
        sf_warehouse=config.SF_WAREHOUSE,
        sf_database=config.SF_DATABASE,
        sf_schema=config.SF_SCHEMA,
        sf_role=config.SF_ROLE,
        sf_authenticator=config.SF_AUTHENTICATOR,
        sf_private_key_file=config.SF_PRIVATE_KEY_PATH,
        sf_private_key_pwd=config.SF_PRIVATE_KEY_PWD,
    )
    if not conn.is_connected():
        print("[ERROR] Key-pair connection failed.")
        return False

    result = conn.execute_query("SELECT CURRENT_USER() AS U, CURRENT_ROLE() AS R, CURRENT_WAREHOUSE() AS W")
    if result:
        r = result[0]
        print(f"[OK] Connected as: {r.get('U')} / role={r.get('R')} / warehouse={r.get('W')}")
    else:
        print("[FAIL] Connected but the verification query returned no rows.")
        return False

    conn.close_connection()
    print("\n[OK] Key-pair authentication is fully working — no more MFA/TOTP prompts for this account.\n")
    print("[NEXT] You can now comment out SF_PASSWORD/SF_PASSCODE (and SNOWFLAKE_*) in .env.")
    print("[NEXT] To rotate the key later: delete rsa_key.p8/rsa_key.pub, re-run")
    print(f"[NEXT]   python scripts/setup_keypair_auth.py --register")
    return True


def main():
    parser = argparse.ArgumentParser(description="Set up Snowflake key-pair (RSA) authentication.")
    parser.add_argument('--keyfile', default=None, help="Path to private .p8 key (default: SF_PRIVATE_KEY_PATH or rsa_key.p8)")
    parser.add_argument('--pubfile', default=None, help="Path to public .pub key (default: same dir as keyfile -> rsa_key.pub)")
    parser.add_argument('--register', action='store_true', help="Run ALTER USER to register the public key (requires password in .env, one-time MFA possible)")
    parser.add_argument('--test', action='store_true', help="Only test the key-pair connection and exit")
    parser.add_argument('--force', action='store_true', help="Regenerate the key pair even if it already exists")
    args = parser.parse_args()

    import config

    key_path = args.keyfile or config.SF_PRIVATE_KEY_PATH
    pub_path = args.pubfile or os.path.join(os.path.dirname(key_path), 'rsa_key.pub')

    if args.test:
        sys.exit(0 if test_keypair_connection() else 1)

    generate_key_pair(key_path, pub_path, force=args.force)
    pub_body = read_pubkey_body(pub_path)

    print("\n" + "=" * 70)
    print(" Register this public key on Snowflake (AccountAdmin):")
    print("=" * 70)
    print(f"ALTER USER {config.SF_USER} SET RSA_PUBLIC_KEY='{pub_body}';")
    print("=" * 70)

    ok = True
    if args.register and not register_public_key(config.SF_USER, pub_body):
        ok = False

    if ok and not test_keypair_connection():
        ok = False

    if not ok:
        print("\n[FAIL] Key-pair setup incomplete — fix the errors above and re-run.")
        sys.exit(1)


if __name__ == '__main__':
    main()