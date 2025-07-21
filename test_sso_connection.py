#!/usr/bin/env python3
"""
Test script to verify SSO connection to Snowflake works properly.
This script tests the updated SnowflakeConnection class with SSO authentication.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.snowflake_db import SnowflakeConnection
from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE

def test_sso_connection():
    """Test the SSO connection to Snowflake."""
    print("🔄 Testing Snowflake SSO Connection...")
    print(f"Account: {SF_ACCOUNT}")
    print(f"User: {SF_USER}")
    print(f"Warehouse: {SF_WAREHOUSE}")
    print(f"Database: {SF_DATABASE}")
    print(f"Schema: {SF_SCHEMA}")
    print(f"Role: {SF_ROLE}")
    print("-" * 50)
    
    try:
        # Create connection using SSO
        conn = SnowflakeConnection(
            sf_account=SF_ACCOUNT,
            sf_user=SF_USER,
            sf_warehouse=SF_WAREHOUSE,
            sf_database=SF_DATABASE,
            sf_schema=SF_SCHEMA,
            sf_role=SF_ROLE
        )
        
        if conn.is_connected():
            print("✅ SSO Connection successful!")
            
            # Test a simple query
            print("\n🔍 Testing simple query...")
            result = conn.execute_query("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
            if result:
                print("✅ Query executed successfully!")
                for row in result:
                    print(f"   User: {row.get('CURRENT_USER()', 'N/A')}")
                    print(f"   Role: {row.get('CURRENT_ROLE()', 'N/A')}")
                    print(f"   Warehouse: {row.get('CURRENT_WAREHOUSE()', 'N/A')}")
            else:
                print("❌ Query failed!")
                
            # Test Cortex LLM call
            print("\n🤖 Testing Cortex LLM...")
            llm_result = conn.call_cortex_llm(
                "What is 2+2? Respond with just the number.",
                model='mixtral-8x7b',
                expect_json=False
            )
            if llm_result:
                print(f"✅ Cortex LLM response: {llm_result}")
            else:
                print("❌ Cortex LLM call failed!")
                
            # Close connection
            conn.close_connection()
            print("\n✅ Connection closed successfully!")
            
        else:
            print("❌ SSO Connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during connection test: {e}")
        return False
        
    return True

def test_reconnection():
    """Test the reconnection functionality."""
    print("\n🔄 Testing reconnection functionality...")
    
    try:
        # Create connection
        conn = SnowflakeConnection(
            sf_account=SF_ACCOUNT,
            sf_user=SF_USER,
            sf_warehouse=SF_WAREHOUSE,
            sf_database=SF_DATABASE,
            sf_schema=SF_SCHEMA,
            sf_role=SF_ROLE
        )
        
        if conn.is_connected():
            print("✅ Initial connection successful!")
            
            # Test reconnection
            print("🔄 Testing reconnection...")
            if conn.reconnect():
                print("✅ Reconnection successful!")
            else:
                print("❌ Reconnection failed!")
                
            conn.close_connection()
            
        else:
            print("❌ Initial connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during reconnection test: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SNOWFLAKE SSO CONNECTION TEST")
    print("=" * 60)
    
    # Check if all required environment variables are set
    required_vars = [SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE]
    if not all(required_vars):
        print("❌ Missing required environment variables!")
        print("Please ensure all Snowflake configuration variables are set in your .env file")
        sys.exit(1)
    
    success = True
    
    # Test basic connection
    if not test_sso_connection():
        success = False
    
    # Test reconnection
    if not test_reconnection():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED! SSO connection is working properly.")
    else:
        print("❌ SOME TESTS FAILED! Please check the errors above.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
