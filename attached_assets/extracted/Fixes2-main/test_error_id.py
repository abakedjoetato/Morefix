#!/usr/bin/env python3
"""
Simple test script to verify ErrorTelemetry.get_error_id functionality
"""
import hashlib
import asyncio
import traceback

# Import error telemetry
try:
    from utils.error_telemetry import ErrorTelemetry, get_error_fingerprint
    print("Successfully imported error telemetry modules")
except ImportError as e:
    print(f"Failed to import error telemetry: {e}")
    exit(1)

async def test():
    """Test error ID generation"""
    print("Testing error ID generation...")
    
    try:
        # Generate a test error
        raise ValueError("Test error message")
    except Exception as e:
        # Get the error ID using our new method
        error_id = await ErrorTelemetry.get_error_id(e)
        print(f"Error ID: {error_id}")
        
        # Get the fingerprint directly
        fingerprint = get_error_fingerprint(e)
        print(f"Fingerprint: {fingerprint}")
        
        # Compare
        print(f"Match: {error_id == fingerprint}")
        
        if error_id == fingerprint:
            print("✅ get_error_id implementation is working correctly!")
        else:
            print("❌ get_error_id implementation is NOT working correctly!")

if __name__ == "__main__":
    try:
        asyncio.run(test())
    except Exception as e:
        print(f"Test failed with error: {e}")
        traceback.print_exc()