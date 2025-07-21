#!/usr/bin/env python3
"""
Test script to verify configuration is properly loaded from .env file.
This script tests that all environment variables are correctly configured for SSO authentication.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test that all configuration variables are properly loaded."""
    print("🔄 Testing Configuration Loading...")
    print("-" * 50)
    
    try:
        from config import (
            SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
            EMAIL_ACCOUNT, EMAIL_PASSWORD, SUPPORT_PHONE, SUPPORT_EMAIL
        )
        
        # Test Snowflake Configuration
        print("📊 Snowflake Configuration:")
        print(f"  Account: {SF_ACCOUNT}")
        print(f"  User: {SF_USER}")
        print(f"  Warehouse: {SF_WAREHOUSE}")
        print(f"  Database: {SF_DATABASE}")
        print(f"  Schema: {SF_SCHEMA}")
        print(f"  Role: {SF_ROLE}")
        
        # Verify all Snowflake variables are set
        sf_vars = [SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE]
        missing_sf = [var for var in sf_vars if not var]
        
        if missing_sf:
            print(f"❌ Missing Snowflake configuration variables: {missing_sf}")
            return False
        else:
            print("✅ All Snowflake configuration variables are set")
        
        print("\n📧 Email Configuration:")
        print(f"  Email Account: {EMAIL_ACCOUNT}")
        print(f"  Email Password: {'*' * len(EMAIL_PASSWORD) if EMAIL_PASSWORD else 'NOT SET'}")
        print(f"  Support Phone: {SUPPORT_PHONE}")
        print(f"  Support Email: {SUPPORT_EMAIL}")
        
        # Verify email variables are set
        if not EMAIL_PASSWORD:
            print("❌ Email password is not set")
            return False
        else:
            print("✅ Email configuration is set")
        
        print("\n🔐 Authentication Method:")
        print("  Using SSO (externalbrowser) authentication")
        print("  No password or MFA passcode required")
        
        print("\n✅ Configuration test completed successfully!")
        print("🚀 Ready to use SSO authentication with Snowflake")
        return True
        
    except ImportError as e:
        print(f"❌ Error importing configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_snowflake_connection_params():
    """Test that Snowflake connection parameters are correctly formatted."""
    print("\n🔧 Testing Snowflake Connection Parameters...")
    print("-" * 50)
    
    try:
        from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE
        
        # Simulate connection parameters (without actually connecting)
        connection_params = {
            'user': SF_USER,
            'account': SF_ACCOUNT,
            'authenticator': 'externalbrowser',  # SSO authentication
            'warehouse': SF_WAREHOUSE,
            'database': SF_DATABASE,
            'schema': SF_SCHEMA,
            'role': SF_ROLE
        }
        
        print("Connection parameters that would be used:")
        for key, value in connection_params.items():
            print(f"  {key}: {value}")
        
        # Verify no password or passcode in parameters
        if 'password' in connection_params or 'passcode' in connection_params:
            print("❌ Found password/passcode in connection parameters - should use SSO only")
            return False
        
        print("✅ Connection parameters are correctly configured for SSO")
        return True
        
    except Exception as e:
        print(f"❌ Error testing connection parameters: {e}")
        return False

if __name__ == "__main__":
    print("🧪 TeamLogic-AutoTask Configuration Test")
    print("=" * 60)
    
    success = True
    success &= test_configuration()
    success &= test_snowflake_connection_params()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Configuration is ready for SSO authentication.")
    else:
        print("❌ Some tests failed. Please check your .env file configuration.")
    
    sys.exit(0 if success else 1)
