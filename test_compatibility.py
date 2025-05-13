"""
Comprehensive Compatibility Test Suite

This script tests all the compatibility layers created for the Tower of Temptation
Discord bot, ensuring they work properly across different Discord library versions.
"""

import asyncio
import inspect
import logging
import unittest
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Import Discord libraries
    import discord
    from discord.ext import commands
    
    # Import our compatibility modules
    from utils.attribute_access import (
        safe_server_getattr,
        safe_member_getattr,
        safe_channel_getattr,
        safe_role_getattr,
        safe_message_getattr
    )
    from utils.async_helpers import (
        is_coroutine_function,
        ensure_async,
        ensure_sync,
        safe_gather,
        safe_wait,
        AsyncCache,
        cached_async
    )
    from utils.command_handlers import (
        EnhancedSlashCommand,
        text_option,
        number_option,
        integer_option,
        boolean_option,
        user_option,
        channel_option,
        role_option,
        enhanced_slash_command,
        is_pycord_261_or_later
    )
    from utils.command_parameter_builder import (
        CommandParameter,
        CommandBuilder
    )
    from utils.event_helpers import (
        EventDispatcher,
        CompatibleBot,
        register_cog_events
    )
    from utils.intent_helpers import (
        get_default_intents,
        get_all_intents,
        get_minimal_intents,
        create_intents,
        merge_intents
    )
    from utils.interaction_handlers import (
        safely_respond_to_interaction,
        hybrid_send,
        is_interaction,
        is_context,
        get_user,
        get_guild,
        get_guild_id
    )
    from utils.mongo_compat import (
        serialize_document,
        deserialize_document,
        is_objectid,
        to_object_id,
        handle_datetime
    )
    from utils.permission_helpers import (
        get_channel_permissions,
        has_permission,
        has_channel_permission,
        format_permissions,
        create_permissions,
        merge_permissions,
        is_admin,
        has_role,
        has_any_role,
        has_all_roles
    )
    from utils.safe_mongodb import (
        SafeMongoDBResult,
        SafeDocument,
        get_collection,
        safe_find_one,
        safe_find,
        safe_insert_one,
        safe_update_one,
        safe_delete_one,
        safe_count
    )
    from utils.type_safety import (
        safe_cast,
        safe_str,
        safe_int,
        safe_float,
        safe_bool,
        safe_list,
        safe_dict,
        safe_function_call,
        validate_type,
        validate_func_args
    )
    
except ImportError as e:
    logger.error(f"Failed to import required libraries: {e}")
    sys.exit(1)

class AttributeAccessTests(unittest.TestCase):
    """Tests for the attribute_access module."""
    
    def test_safe_getattr(self):
        """Test the safe_getattr functions."""
        # Create a mock object
        class MockObject:
            def __init__(self):
                self.name = "Test"
                self.id = 123
                
        obj = MockObject()
        
        # Test safe_server_getattr
        self.assertEqual(safe_server_getattr(obj, "name"), "Test")
        self.assertEqual(safe_server_getattr(obj, "id"), 123)
        self.assertEqual(safe_server_getattr(obj, "missing", "default"), "default")
        
        # Test with None
        self.assertIsNone(safe_server_getattr(None, "name"))
        self.assertEqual(safe_server_getattr(None, "name", "default"), "default")

class AsyncHelpersTests(unittest.IsolatedAsyncioTestCase):
    """Tests for the async_helpers module."""
    
    def test_is_coroutine_function(self):
        """Test is_coroutine_function."""
        async def async_func():
            pass
            
        def sync_func():
            pass
            
        self.assertTrue(is_coroutine_function(async_func))
        self.assertFalse(is_coroutine_function(sync_func))
    
    async def test_ensure_async(self):
        """Test ensure_async."""
        def sync_func():
            return "sync"
            
        async def async_func():
            return "async"
            
        sync_as_async = ensure_async(sync_func)
        self.assertTrue(is_coroutine_function(sync_as_async))
        self.assertEqual(await sync_as_async(), "sync")
        
        # Test with already async function
        same_async = ensure_async(async_func)
        self.assertTrue(is_coroutine_function(same_async))
        self.assertEqual(await same_async(), "async")
    
    async def test_safe_gather(self):
        """Test safe_gather."""
        async def success():
            return "success"
            
        async def failure():
            raise ValueError("failure")
            
        # Test with success only
        results = await safe_gather(success(), success())
        self.assertEqual(results, ["success", "success"])
        
        # Test with failure and return_exceptions=True
        results = await safe_gather(success(), failure(), return_exceptions=True)
        self.assertEqual(results[0], "success")
        self.assertIsInstance(results[1], ValueError)
        
    async def test_async_cache(self):
        """Test AsyncCache."""
        cache = AsyncCache(ttl=0.1)
        
        # Test set and get
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # Test expiration
        cache.set("key2", "value2")
        await asyncio.sleep(0.2)  # Wait for TTL to expire
        self.assertIsNone(cache.get("key2"))
        
        # Test get_or_set
        value = cache.get_or_set("key3", lambda: "value3")
        self.assertEqual(value, "value3")
        
        # Test get_or_set_async
        async def get_value():
            return "value4"
            
        value = await cache.get_or_set_async("key4", get_value)
        self.assertEqual(value, "value4")

class CommandHandlersTests(unittest.TestCase):
    """Tests for the command_handlers module."""
    
    def test_option_builders(self):
        """Test the option builder functions."""
        # Test text_option
        option = text_option("name", "description", required=True, default="default")
        self.assertEqual(option["name"], "name")
        self.assertEqual(option["description"], "description")
        self.assertEqual(option["required"], True)
        self.assertEqual(option["type"], str)
        self.assertEqual(option["default"], "default")
        
        # Test number_option
        option = number_option("age", "Age in years", required=False, default=18.5)
        self.assertEqual(option["name"], "age")
        self.assertEqual(option["description"], "Age in years")
        self.assertEqual(option["required"], False)
        self.assertEqual(option["type"], float)
        self.assertEqual(option["default"], 18.5)
        
        # Test integer_option
        option = integer_option("count", "Count of items", required=True)
        self.assertEqual(option["name"], "count")
        self.assertEqual(option["description"], "Count of items")
        self.assertEqual(option["required"], True)
        self.assertEqual(option["type"], int)
        
        # Test boolean_option
        option = boolean_option("enabled", "Whether feature is enabled", default=True)
        self.assertEqual(option["name"], "enabled")
        self.assertEqual(option["description"], "Whether feature is enabled")
        self.assertEqual(option["type"], bool)
        self.assertEqual(option["default"], True)

class CommandParameterBuilderTests(unittest.TestCase):
    """Tests for the command_parameter_builder module."""
    
    def test_command_parameter(self):
        """Test CommandParameter."""
        param = CommandParameter(
            name="test",
            description="Test parameter",
            type=str,
            required=True,
            default="default",
            choices=["option1", "option2"],
            min_value=None,
            max_value=None
        )
        
        self.assertEqual(param.name, "test")
        self.assertEqual(param.description, "Test parameter")
        self.assertEqual(param.type, str)
        self.assertEqual(param.required, True)
        self.assertEqual(param.default, "default")
        self.assertEqual(param.choices, ["option1", "option2"])
        
        # Test to_dict
        param_dict = param.to_dict()
        self.assertEqual(param_dict["name"], "test")
        self.assertEqual(param_dict["description"], "Test parameter")
        self.assertEqual(param_dict["type"], str)
        self.assertEqual(param_dict["required"], True)
        self.assertEqual(param_dict["default"], "default")
        self.assertEqual(param_dict["choices"], ["option1", "option2"])
    
    def test_command_builder(self):
        """Test CommandBuilder."""
        def callback():
            pass
            
        builder = CommandBuilder(
            name="test",
            description="Test command",
            callback=callback,
            guild_ids=[123, 456]
        )
        
        # Test adding parameters
        builder.add_string_parameter(
            name="text",
            description="Text parameter",
            required=True,
            default="default",
            choices=["option1", "option2"]
        )
        
        builder.add_integer_parameter(
            name="count",
            description="Count parameter",
            required=False,
            default=0,
            min_value=0,
            max_value=100
        )
        
        self.assertEqual(len(builder.parameters), 2)
        self.assertIn("text", builder.parameters)
        self.assertIn("count", builder.parameters)

class EventHelpersTests(unittest.IsolatedAsyncioTestCase):
    """Tests for the event_helpers module."""
    
    async def test_event_dispatcher(self):
        """Test EventDispatcher."""
        dispatcher = EventDispatcher()
        
        # Create event listeners
        events_called = []
        
        async def on_event1(*args, **kwargs):
            events_called.append(("event1", args, kwargs))
            
        async def on_event2(*args, **kwargs):
            events_called.append(("event2", args, kwargs))
            
        # Register listeners
        dispatcher.register_listener("event1", on_event1)
        dispatcher.register_listener("event2", on_event2, once=True)
        
        # Dispatch events
        await dispatcher.dispatch("event1", "arg1", "arg2", key="value")
        await dispatcher.dispatch("event2", 123, 456, flag=True)
        
        # Check results
        self.assertEqual(len(events_called), 2)
        self.assertEqual(events_called[0][0], "event1")
        self.assertEqual(events_called[0][1], ("arg1", "arg2"))
        self.assertEqual(events_called[0][2], {"key": "value"})
        
        self.assertEqual(events_called[1][0], "event2")
        self.assertEqual(events_called[1][1], (123, 456))
        self.assertEqual(events_called[1][2], {"flag": True})
        
        # Test once listener is removed
        events_called.clear()
        await dispatcher.dispatch("event1")
        await dispatcher.dispatch("event2")
        self.assertEqual(len(events_called), 1)
        self.assertEqual(events_called[0][0], "event1")

class IntentHelpersTests(unittest.TestCase):
    """Tests for the intent_helpers module."""
    
    def test_get_default_intents(self):
        """Test get_default_intents."""
        intents = get_default_intents()
        self.assertIsInstance(intents, discord.Intents)
        self.assertTrue(intents.guilds)
        self.assertTrue(intents.members)
    
    def test_create_intents(self):
        """Test create_intents."""
        intents = create_intents(
            guilds=True,
            members=True,
            guild_messages=True,
            dm_messages=False
        )
        self.assertIsInstance(intents, discord.Intents)
        self.assertTrue(intents.guilds)
        self.assertTrue(intents.members)
        
        # Depending on Discord library version, check the appropriate attributes
        if hasattr(intents, "guild_messages"):
            self.assertTrue(intents.guild_messages)
            self.assertFalse(intents.dm_messages)
        elif hasattr(intents, "messages"):
            self.assertTrue(intents.messages)
    
    def test_merge_intents(self):
        """Test merge_intents."""
        intents1 = create_intents(guilds=True, members=False)
        intents2 = create_intents(guilds=False, members=True)
        
        merged = merge_intents(intents1, intents2)
        self.assertTrue(merged.guilds)
        self.assertTrue(merged.members)

class InteractionHandlersTests(unittest.TestCase):
    """Tests for the interaction_handlers module."""
    
    def test_is_interaction_and_context(self):
        """Test is_interaction and is_context functions."""
        # Creating mock objects
        class MockInteraction:
            def __init__(self):
                self.response = None
                
        class MockContext:
            def __init__(self):
                self.bot = None
                
        interaction = MockInteraction()
        context = MockContext()
        
        self.assertTrue(is_interaction(interaction))
        self.assertFalse(is_interaction(context))
        
        self.assertTrue(is_context(context))
        self.assertFalse(is_context(interaction))
    
    def test_get_user_and_guild(self):
        """Test get_user and get_guild functions."""
        # Creating mock objects
        class MockUser:
            def __init__(self):
                self.id = 123
                
        class MockGuild:
            def __init__(self):
                self.id = 456
                
        class MockInteraction:
            def __init__(self):
                self.user = MockUser()
                self.guild = MockGuild()
                
        class MockContext:
            def __init__(self):
                self.author = MockUser()
                self.guild = MockGuild()
                
        interaction = MockInteraction()
        context = MockContext()
        
        # Test get_user
        user = get_user(interaction)
        self.assertEqual(user.id, 123)
        
        user = get_user(context)
        self.assertEqual(user.id, 123)
        
        # Test get_guild
        guild = get_guild(interaction)
        self.assertEqual(guild.id, 456)
        
        guild = get_guild(context)
        self.assertEqual(guild.id, 456)
        
        # Test get_guild_id
        guild_id = get_guild_id(interaction)
        self.assertEqual(guild_id, 456)
        
        guild_id = get_guild_id(context)
        self.assertEqual(guild_id, 456)

class MongoCompatTests(unittest.TestCase):
    """Tests for the mongo_compat module."""
    
    def test_serialize_deserialize_document(self):
        """Test serialize_document and deserialize_document."""
        from datetime import datetime
        
        # Create a test document
        doc = {
            "name": "Test",
            "created_at": datetime.utcnow(),
            "count": 123,
            "active": True,
            "nested": {
                "key": "value",
                "timestamp": datetime.utcnow()
            }
        }
        
        # Serialize the document
        serialized = serialize_document(doc)
        
        # Check that datetimes were converted to strings
        self.assertIsInstance(serialized["created_at"], str)
        self.assertIsInstance(serialized["nested"]["timestamp"], str)
        
        # Deserialize the document
        deserialized = deserialize_document(serialized)
        
        # Check that strings were converted back to datetimes
        self.assertIsInstance(deserialized["created_at"], datetime)
        self.assertIsInstance(deserialized["nested"]["timestamp"], datetime)

class PermissionHelpersTests(unittest.TestCase):
    """Tests for the permission_helpers module."""
    
    def test_create_and_merge_permissions(self):
        """Test create_permissions and merge_permissions functions."""
        # Create permissions
        perms1 = create_permissions(
            read_messages=True,
            send_messages=True,
            manage_messages=False
        )
        
        perms2 = create_permissions(
            read_messages=False,
            manage_messages=True,
            manage_channels=True
        )
        
        # Test the permissions
        self.assertTrue(perms1.read_messages)
        self.assertTrue(perms1.send_messages)
        self.assertFalse(perms1.manage_messages)
        
        self.assertFalse(perms2.read_messages)
        self.assertTrue(perms2.manage_messages)
        self.assertTrue(perms2.manage_channels)
        
        # Merge permissions
        merged = merge_permissions(perms1, perms2)
        
        # Test merged permissions
        self.assertTrue(merged.read_messages)
        self.assertTrue(merged.send_messages)
        self.assertTrue(merged.manage_messages)
        self.assertTrue(merged.manage_channels)
    
    def test_format_permissions(self):
        """Test format_permissions function."""
        perms = create_permissions(
            read_messages=True,
            send_messages=True,
            manage_messages=True
        )
        
        formatted = format_permissions(perms)
        self.assertIn("Read Messages", formatted)
        self.assertIn("Send Messages", formatted)
        self.assertIn("Manage Messages", formatted)

class SafeMongoDBTests(unittest.TestCase):
    """Tests for the safe_mongodb module."""
    
    def test_safe_mongodb_result(self):
        """Test SafeMongoDBResult."""
        # Create a mock MongoDB result
        class MockResult:
            def __init__(self):
                self.acknowledged = True
                self.inserted_id = "abc123"
                self.modified_count = 1
                self.matched_count = 2
                self.deleted_count = 0
                self.upserted_id = None
                
        result = MockResult()
        safe_result = SafeMongoDBResult(result)
        
        # Test attributes
        self.assertTrue(safe_result.acknowledged)
        self.assertEqual(safe_result.inserted_id, "abc123")
        self.assertEqual(safe_result.modified_count, 1)
        self.assertEqual(safe_result.matched_count, 2)
        self.assertEqual(safe_result.deleted_count, 0)
        self.assertIsNone(safe_result.upserted_id)
        
        # Test with missing attributes
        class PartialResult:
            def __init__(self):
                self.acknowledged = True
                # Missing other attributes
                
        partial_result = PartialResult()
        safe_partial = SafeMongoDBResult(partial_result)
        
        self.assertTrue(safe_partial.acknowledged)
        self.assertIsNone(safe_partial.inserted_id)
        self.assertEqual(safe_partial.modified_count, 0)
        self.assertEqual(safe_partial.matched_count, 0)
        self.assertEqual(safe_partial.deleted_count, 0)
        self.assertIsNone(safe_partial.upserted_id)
    
    def test_safe_document(self):
        """Test SafeDocument."""
        # Create a document
        doc = {
            "id": "abc123",
            "name": "Test",
            "count": 123,
            "nested": {
                "key": "value"
            }
        }
        
        safe_doc = SafeDocument(doc)
        
        # Test property access
        self.assertEqual(safe_doc.id, "abc123")
        self.assertEqual(safe_doc.name, "Test")
        self.assertEqual(safe_doc.count, 123)
        self.assertIsInstance(safe_doc.nested, dict)
        self.assertEqual(safe_doc.nested["key"], "value")
        
        # Test property access with default
        self.assertIsNone(safe_doc.missing)
        self.assertEqual(safe_doc.get("missing", "default"), "default")
        
        # Test dictionary access
        self.assertEqual(safe_doc["id"], "abc123")
        self.assertEqual(safe_doc["name"], "Test")
        
        # Test to_dict
        self.assertEqual(safe_doc.to_dict(), doc)

class TypeSafetyTests(unittest.TestCase):
    """Tests for the type_safety module."""
    
    def test_safe_cast(self):
        """Test safe_cast function."""
        # Test basic types
        self.assertEqual(safe_cast("123", int), 123)
        self.assertEqual(safe_cast("123.45", float), 123.45)
        self.assertEqual(safe_cast(123, str), "123")
        self.assertEqual(safe_cast("true", bool), True)
        self.assertEqual(safe_cast("false", bool), False)
        
        # Test with default
        self.assertEqual(safe_cast("abc", int, 0), 0)
        
        # Test with None
        self.assertIsNone(safe_cast(None, int))
        self.assertEqual(safe_cast(None, int, 0), 0)
    
    def test_safe_str(self):
        """Test safe_str function."""
        self.assertEqual(safe_str(123), "123")
        self.assertEqual(safe_str(123.45), "123.45")
        self.assertEqual(safe_str(True), "True")
        self.assertEqual(safe_str(None), "")
        
        # Test with max_length
        long_str = "x" * 100
        self.assertEqual(len(safe_str(long_str, max_length=50)), 50)
    
    def test_safe_int(self):
        """Test safe_int function."""
        self.assertEqual(safe_int("123"), 123)
        self.assertEqual(safe_int(123.45), 123)
        self.assertEqual(safe_int(True), 1)
        self.assertEqual(safe_int(False), 0)
        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int("abc", 42), 42)
    
    def test_safe_float(self):
        """Test safe_float function."""
        self.assertEqual(safe_float("123.45"), 123.45)
        self.assertEqual(safe_float(123), 123.0)
        self.assertEqual(safe_float(True), 1.0)
        self.assertEqual(safe_float(False), 0.0)
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float("abc", 42.5), 42.5)
    
    def test_safe_bool(self):
        """Test safe_bool function."""
        self.assertTrue(safe_bool("true"))
        self.assertTrue(safe_bool("yes"))
        self.assertTrue(safe_bool("1"))
        self.assertTrue(safe_bool(1))
        self.assertTrue(safe_bool(True))
        
        self.assertFalse(safe_bool("false"))
        self.assertFalse(safe_bool("no"))
        self.assertFalse(safe_bool("0"))
        self.assertFalse(safe_bool(0))
        self.assertFalse(safe_bool(False))
        self.assertFalse(safe_bool(None))
    
    def test_safe_list(self):
        """Test safe_list function."""
        self.assertEqual(safe_list([1, 2, 3]), [1, 2, 3])
        self.assertEqual(safe_list((1, 2, 3)), [1, 2, 3])
        self.assertEqual(safe_list("abc"), ["abc"])
        self.assertEqual(safe_list(123), [123])
        self.assertEqual(safe_list(None), [])
        
        # Test with item_type
        self.assertEqual(safe_list(["1", "2", "3"], int), [1, 2, 3])
    
    def test_safe_dict(self):
        """Test safe_dict function."""
        self.assertEqual(safe_dict({"a": 1, "b": 2}), {"a": 1, "b": 2})
        self.assertEqual(safe_dict([("a", 1), ("b", 2)]), {"a": 1, "b": 2})
        self.assertEqual(safe_dict(None), {})
        
        # Test with object that has __dict__
        class TestObj:
            def __init__(self):
                self.a = 1
                self.b = 2
                self._private = 3
                
        obj = TestObj()
        self.assertEqual(safe_dict(obj), {"a": 1, "b": 2})
    
    def test_validate_type(self):
        """Test validate_type function."""
        self.assertTrue(validate_type(123, int))
        self.assertTrue(validate_type("abc", str))
        self.assertTrue(validate_type(123.45, float))
        self.assertTrue(validate_type(True, bool))
        
        self.assertFalse(validate_type("123", int))
        self.assertFalse(validate_type(123, str))
        
        # Test with Union
        from typing import Union
        self.assertTrue(validate_type(123, Union[int, str]))
        self.assertTrue(validate_type("abc", Union[int, str]))
        self.assertFalse(validate_type(123.45, Union[int, str]))
        
        # Test with List
        from typing import List
        self.assertTrue(validate_type([1, 2, 3], List[int]))
        self.assertFalse(validate_type([1, "2", 3], List[int]))
        
        # Test with Dict
        from typing import Dict
        self.assertTrue(validate_type({"a": 1, "b": 2}, Dict[str, int]))
        self.assertFalse(validate_type({"a": 1, "b": "2"}, Dict[str, int]))

def run_tests():
    """Run all tests."""
    test_classes = [
        AttributeAccessTests,
        AsyncHelpersTests,
        CommandHandlersTests,
        CommandParameterBuilderTests,
        EventHelpersTests,
        IntentHelpersTests,
        InteractionHandlersTests,
        MongoCompatTests,
        PermissionHelpersTests,
        SafeMongoDBTests,
        TypeSafetyTests
    ]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
        
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)

if __name__ == "__main__":
    print("Running compatibility tests...")
    result = run_tests()
    
    if result.wasSuccessful():
        print("\nAll tests passed successfully!")
        sys.exit(0)
    else:
        print(f"\nTests failed: {len(result.errors)} errors, {len(result.failures)} failures")
        sys.exit(1)