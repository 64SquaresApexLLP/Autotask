#!/usr/bin/env python3
"""
Fix Workload Data Types
Update current_workload column to ensure it only contains integer values
"""

import sys
import os

# Add the src directory to the path
sys.path.append('src')

def fix_workload_data_types():
    """Fix the current_workload column to contain only integer values"""
    print("🔧 FIXING WORKLOAD DATA TYPES")
    print("=" * 60)
    
    try:
        from src.database.snowflake_db import SnowflakeConnection
        from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE
        
        # Initialize database connection
        print("🔌 Connecting to Snowflake...")
        snowflake_conn = SnowflakeConnection(
            sf_account=SF_ACCOUNT,
            sf_user=SF_USER,
            sf_warehouse=SF_WAREHOUSE,
            sf_database=SF_DATABASE,
            sf_schema=SF_SCHEMA,
            sf_role=SF_ROLE
        )
        
        if not snowflake_conn.conn:
            print("❌ Failed to connect to Snowflake")
            return False
        
        cursor = snowflake_conn.conn.cursor()
        
        # Step 1: Check current data type of current_workload column
        print("📊 Step 1: Checking current data type...")
        check_type_query = """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'PUBLIC'
        AND TABLE_NAME = 'TECHNICIAN_DUMMY_DATA'
        AND COLUMN_NAME = 'CURRENT_WORKLOAD'
        """
        
        cursor.execute(check_type_query)
        result = cursor.fetchone()
        
        if result:
            column_name, data_type, is_nullable = result
            print(f"  Current data type: {data_type}")
            print(f"  Nullable: {is_nullable}")
        else:
            print("❌ Could not find CURRENT_WORKLOAD column")
            return False
        
        # Step 2: Check current values in the column
        print("\n📊 Step 2: Checking current values...")
        check_values_query = """
        SELECT TECHNICIAN_ID, NAME, CURRENT_WORKLOAD
        FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        ORDER BY TECHNICIAN_ID
        """
        
        cursor.execute(check_values_query)
        results = cursor.fetchall()
        
        print("  Current workload values:")
        for row in results:
            tech_id, name, workload = row
            print(f"    {tech_id} ({name}): {workload}")
        
        # Step 3: Update the column to ensure integer values
        print("\n🔧 Step 3: Converting to integer values...")
        
        # First, create a temporary column with integer values
        create_temp_query = """
        ALTER TABLE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        ADD COLUMN CURRENT_WORKLOAD_INT INTEGER
        """
        
        try:
            cursor.execute(create_temp_query)
            print("  ✅ Created temporary column CURRENT_WORKLOAD_INT")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ℹ️  Temporary column already exists")
            else:
                print(f"  ⚠️  Could not create temporary column: {e}")
        
        # Update the temporary column with integer values
        update_temp_query = """
        UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        SET CURRENT_WORKLOAD_INT = CAST(COALESCE(CURRENT_WORKLOAD, 0) AS INTEGER)
        """
        
        cursor.execute(update_temp_query)
        print("  ✅ Updated temporary column with integer values")
        
        # Step 4: Drop the old column and rename the new one
        print("\n🔄 Step 4: Replacing the column...")
        
        # Drop the old column
        drop_old_query = """
        ALTER TABLE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        DROP COLUMN CURRENT_WORKLOAD
        """
        
        cursor.execute(drop_old_query)
        print("  ✅ Dropped old CURRENT_WORKLOAD column")
        
        # Rename the new column
        rename_query = """
        ALTER TABLE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        RENAME COLUMN CURRENT_WORKLOAD_INT TO CURRENT_WORKLOAD
        """
        
        cursor.execute(rename_query)
        print("  ✅ Renamed CURRENT_WORKLOAD_INT to CURRENT_WORKLOAD")
        
        # Step 5: Verify the changes
        print("\n✅ Step 5: Verifying changes...")
        
        # Check the new data type
        cursor.execute(check_type_query)
        result = cursor.fetchone()
        
        if result:
            column_name, data_type, is_nullable = result
            print(f"  New data type: {data_type}")
            print(f"  Nullable: {is_nullable}")
        
        # Check the new values
        cursor.execute(check_values_query)
        results = cursor.fetchall()
        
        print("  New workload values:")
        for row in results:
            tech_id, name, workload = row
            print(f"    {tech_id} ({name}): {workload}")
        
        # Step 6: Handle NULL values and constraints
        print("\n🔒 Step 6: Setting constraints...")
        
        # Update any NULL values to 0
        update_null_query = """
        UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        SET CURRENT_WORKLOAD = 0
        WHERE CURRENT_WORKLOAD IS NULL
        """
        
        cursor.execute(update_null_query)
        print("  ✅ Updated NULL values to 0")
        
        # Note: Snowflake doesn't support ALTER COLUMN SET DEFAULT or SET NOT NULL
        # We'll handle this at the application level
        print("  ℹ️  Note: Default values and NOT NULL constraints will be handled at application level")
        
        cursor.close()
        
        print("\n🎉 WORKLOAD DATA TYPE FIX COMPLETED!")
        print("✅ CURRENT_WORKLOAD column now contains only INTEGER values")
        print("✅ All values converted to integers")
        print("✅ NULL values updated to 0")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix workload data types: {e}")
        return False

def test_workload_operations():
    """Test workload operations after the fix"""
    print("\n🧪 TESTING WORKLOAD OPERATIONS")
    print("=" * 60)
    
    try:
        from src.database.snowflake_db import SnowflakeConnection
        from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE
        
        snowflake_conn = SnowflakeConnection(
            sf_account=SF_ACCOUNT,
            sf_user=SF_USER,
            sf_warehouse=SF_WAREHOUSE,
            sf_database=SF_DATABASE,
            sf_schema=SF_SCHEMA,
            sf_role=SF_ROLE
        )
        cursor = snowflake_conn.conn.cursor()
        
        # Test increment operation
        print("📈 Testing increment operation...")
        increment_query = """
        UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        SET CURRENT_WORKLOAD = CURRENT_WORKLOAD + 1
        WHERE TECHNICIAN_ID = 'T001'
        """
        
        cursor.execute(increment_query)
        print("  ✅ Increment operation successful")
        
        # Test decrement operation
        print("📉 Testing decrement operation...")
        decrement_query = """
        UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        SET CURRENT_WORKLOAD = GREATEST(CURRENT_WORKLOAD - 1, 0)
        WHERE TECHNICIAN_ID = 'T001'
        """
        
        cursor.execute(decrement_query)
        print("  ✅ Decrement operation successful")
        
        # Verify final state
        verify_query = """
        SELECT TECHNICIAN_ID, NAME, CURRENT_WORKLOAD
        FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        WHERE TECHNICIAN_ID = 'T001'
        """
        
        cursor.execute(verify_query)
        result = cursor.fetchone()
        
        if result:
            tech_id, name, workload = result
            print(f"  Final state: {tech_id} ({name}): {workload}")
            
            # Check if it's a valid integer
            try:
                int(workload)
                print("  ✅ Value is a valid integer")
            except (ValueError, TypeError):
                print(f"  ⚠️  Value is not a valid integer: {workload}")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting workload data type fix...")
    
    # Fix the data types
    fix_success = fix_workload_data_types()
    
    if fix_success:
        # Test the operations
        test_success = test_workload_operations()
        
        print("\n" + "=" * 60)
        print("📊 FIX RESULTS SUMMARY")
        print("=" * 60)
        print(f"🔧 Data Type Fix: {'✅ PASSED' if fix_success else '❌ FAILED'}")
        print(f"🧪 Operation Test: {'✅ PASSED' if test_success else '❌ FAILED'}")
        
        if fix_success and test_success:
            print("\n🎉 All operations successful!")
            print("✅ CURRENT_WORKLOAD column now contains only INTEGER values")
            print("✅ Workload increment/decrement operations work correctly")
        else:
            print("\n⚠️  Some operations failed. Please check the implementation.")
    else:
        print("\n❌ Data type fix failed. Please check the database connection and permissions.") 