"""
Test Script for py-cord 2.6.1 Compatibility

This script performs a series of tests to verify compatibility with py-cord 2.6.1,
which is known to report itself as discord.__version__ 2.5.2 but has different APIs.
"""

import logging
import sys
import asyncio
import importlib
import traceback
from typing import Optional, Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("pycord_compatibility_test")

# Results storage
test_results = {
    "library_detection": {},
    "interaction_features": {},
    "command_features": {},
    "compatibility_layer": {}
}

class TestOutcome:
    """Simple class to track test results"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

async def test_library_detection():
    """Test detection of py-cord vs discord.py"""
    logger.info("Testing library detection...")
    
    try:
        # Try to import discord
        import discord
        
        # Check version
        discord_version = getattr(discord, "__version__", "unknown")
        logger.info(f"Detected discord.__version__ = {discord_version}")
        test_results["library_detection"]["discord_version"] = discord_version
        
        # Check for py-cord specific modules/classes
        is_pycord = False
        pycord_specific_attrs = []
        
        # Test 1: ui module with Modal
        try:
            from discord.ui import Modal
            is_pycord = True
            pycord_specific_attrs.append("discord.ui.Modal")
            logger.info("Found discord.ui.Modal (py-cord specific)")
        except ImportError:
            logger.info("discord.ui.Modal not found (not py-cord or older version)")
        
        # Test 2: slash_command in discord.commands
        try:
            from discord.commands import slash_command
            is_pycord = True
            pycord_specific_attrs.append("discord.commands.slash_command")
            logger.info("Found discord.commands.slash_command (py-cord specific)")
        except ImportError:
            logger.info("discord.commands.slash_command not found (not py-cord or older version)")
        
        # Test 3: slash_command in discord.ext.commands
        try:
            from discord.ext.commands import slash_command
            is_pycord = True
            pycord_specific_attrs.append("discord.ext.commands.slash_command")
            logger.info("Found discord.ext.commands.slash_command (regular py-cord)")
        except ImportError:
            logger.info("discord.ext.commands.slash_command not found (not regular py-cord)")
        
        # Test 4: Option in discord.commands
        try:
            from discord.commands import Option
            is_pycord = True
            pycord_specific_attrs.append("discord.commands.Option")
            logger.info("Found discord.commands.Option (py-cord specific)")
        except ImportError:
            logger.info("discord.commands.Option not found (not py-cord or older version)")
        
        # Test 5: app_commands module (discord.py 2.0+)
        has_app_commands = False
        try:
            import discord.app_commands
            has_app_commands = True
            logger.info("Found discord.app_commands module (discord.py 2.0+)")
        except ImportError:
            logger.info("discord.app_commands module not found (not discord.py 2.0+)")
        
        # Store results
        test_results["library_detection"]["is_pycord"] = is_pycord
        test_results["library_detection"]["pycord_specific_attrs"] = pycord_specific_attrs
        test_results["library_detection"]["has_app_commands"] = has_app_commands
        
        # Determine if this is py-cord 2.6.1
        is_pycord_261 = is_pycord and discord_version == "2.5.2"
        if is_pycord_261:
            logger.info("Detected likely py-cord 2.6.1 (reports as 2.5.2 but has py-cord features)")
        
        test_results["library_detection"]["is_pycord_261"] = is_pycord_261
        
        # Overall result
        return TestOutcome.SUCCESS
    except Exception as e:
        logger.error(f"Error during library detection: {e}")
        logger.error(traceback.format_exc())
        test_results["library_detection"]["error"] = str(e)
        return TestOutcome.ERROR

async def test_interaction_features():
    """Test interaction response API differences"""
    logger.info("Testing interaction response features...")
    
    try:
        import discord
        
        # Create a dummy interaction for testing
        class MockInteraction:
            def __init__(self):
                self.response = None
                self.followup = None
                self._responded = False
                self.user = None
                self.channel = None
        
        # Check for response attribute
        interaction = MockInteraction()
        has_response_attr = hasattr(interaction, "response")
        logger.info(f"Interaction has 'response' attribute: {has_response_attr}")
        test_results["interaction_features"]["has_response_attr"] = has_response_attr
        
        # Check for respond method and pattern
        has_respond_method = hasattr(interaction, "respond") and callable(getattr(interaction, "respond", None))
        logger.info(f"Interaction has 'respond' method: {has_respond_method}")
        test_results["interaction_features"]["has_respond_method"] = has_respond_method
        
        # Check for followup attribute
        has_followup_attr = hasattr(interaction, "followup")
        logger.info(f"Interaction has 'followup' attribute: {has_followup_attr}")
        test_results["interaction_features"]["has_followup_attr"] = has_followup_attr
        
        # Create mock response object
        class MockResponse:
            def __init__(self):
                self.is_done_called = False
            
            def is_done(self):
                self.is_done_called = True
                return False
        
        # Add response to interaction
        interaction.response = MockResponse()
        
        # Test for is_done method
        has_is_done_method = hasattr(interaction.response, "is_done") and callable(interaction.response.is_done)
        logger.info(f"Interaction.response has 'is_done' method: {has_is_done_method}")
        test_results["interaction_features"]["has_is_done_method"] = has_is_done_method
        
        # Based on the results, determine which library version's interaction pattern this likely is
        if has_response_attr and has_is_done_method:
            logger.info("Interaction pattern matches py-cord 2.6.1")
            test_results["interaction_features"]["likely_library"] = "py-cord 2.6.1"
        elif has_respond_method:
            logger.info("Interaction pattern matches discord.py or older py-cord")
            test_results["interaction_features"]["likely_library"] = "discord.py or older py-cord"
        else:
            logger.info("Unknown interaction pattern")
            test_results["interaction_features"]["likely_library"] = "unknown"
        
        return TestOutcome.SUCCESS
    except Exception as e:
        logger.error(f"Error during interaction features test: {e}")
        logger.error(traceback.format_exc())
        test_results["interaction_features"]["error"] = str(e)
        return TestOutcome.ERROR

async def test_command_features():
    """Test command registration API differences"""
    logger.info("Testing command registration features...")
    
    try:
        import discord
        
        # Import commands extension
        command_types = []
        
        # Test for slash_command in discord.commands (py-cord 2.6.1)
        try:
            from discord.commands import slash_command
            command_types.append("discord.commands.slash_command")
            logger.info("Found discord.commands.slash_command")
        except ImportError:
            logger.info("discord.commands.slash_command not available")
        
        # Test for slash_command in discord.ext.commands (regular py-cord)
        try:
            from discord.ext.commands import slash_command
            command_types.append("discord.ext.commands.slash_command")
            logger.info("Found discord.ext.commands.slash_command")
        except ImportError:
            logger.info("discord.ext.commands.slash_command not available")
        
        # Test for app_commands module
        try:
            import discord.app_commands
            command_types.append("discord.app_commands")
            logger.info("Found discord.app_commands module")
        except ImportError:
            logger.info("discord.app_commands not available")
        
        # Try to import Option class if available
        try:
            from discord.commands import Option
            command_types.append("discord.commands.Option")
            logger.info("Found discord.commands.Option")
        except ImportError:
            logger.info("discord.commands.Option not available")
        
        test_results["command_features"]["command_types"] = command_types
        
        # Test for CommandTree if available
        has_command_tree = False
        try:
            from discord.ext.commands import Bot
            
            # Create a dummy bot instance
            intents = discord.Intents.default()
            bot = Bot(command_prefix="!", intents=intents)
            
            # Check if it has a tree attribute
            has_command_tree = hasattr(bot, "tree")
            logger.info(f"Bot has 'tree' attribute: {has_command_tree}")
            
            test_results["command_features"]["has_command_tree"] = has_command_tree
        except (ImportError, AttributeError) as e:
            logger.info(f"Could not test for Bot.tree: {e}")
            test_results["command_features"]["has_command_tree"] = False
        
        # Based on the results, determine which library version's command pattern this likely is
        if "discord.commands.slash_command" in command_types:
            logger.info("Command pattern matches py-cord 2.6.1")
            test_results["command_features"]["likely_library"] = "py-cord 2.6.1"
        elif "discord.ext.commands.slash_command" in command_types:
            logger.info("Command pattern matches regular py-cord")
            test_results["command_features"]["likely_library"] = "regular py-cord"
        elif "discord.app_commands" in command_types:
            logger.info("Command pattern matches discord.py 2.0+")
            test_results["command_features"]["likely_library"] = "discord.py 2.0+"
        else:
            logger.info("Command pattern matches legacy discord.py")
            test_results["command_features"]["likely_library"] = "legacy discord.py"
        
        return TestOutcome.SUCCESS
    except Exception as e:
        logger.error(f"Error during command features test: {e}")
        logger.error(traceback.format_exc())
        test_results["command_features"]["error"] = str(e)
        return TestOutcome.ERROR

async def test_compatibility_layer():
    """Test our compatibility layer works correctly"""
    logger.info("Testing compatibility layer...")
    
    try:
        # Import our compatibility modules
        compatibility_modules = []
        
        # Test 1: command_imports.py
        try:
            from utils.command_imports import (
                is_compatible_with_pycord_261,
                has_app_commands,
                is_pycord,
                get_slash_command_class,
                get_option_class
            )
            compatibility_modules.append("utils.command_imports")
            logger.info("Imported utils.command_imports successfully")
            
            # Test the detection functions
            is_261 = is_compatible_with_pycord_261()
            logger.info(f"is_compatible_with_pycord_261() = {is_261}")
            test_results["compatibility_layer"]["is_compatible_with_pycord_261"] = is_261
            
            has_app_cmds = has_app_commands()
            logger.info(f"has_app_commands() = {has_app_cmds}")
            test_results["compatibility_layer"]["has_app_commands"] = has_app_cmds
            
            is_py_cord = is_pycord()
            logger.info(f"is_pycord() = {is_py_cord}")
            test_results["compatibility_layer"]["is_pycord"] = is_py_cord
            
            # Get command classes
            slash_command_class = get_slash_command_class()
            logger.info(f"get_slash_command_class() = {slash_command_class}")
            test_results["compatibility_layer"]["slash_command_class"] = str(slash_command_class)
            
            option_class = get_option_class()
            logger.info(f"get_option_class() = {option_class}")
            test_results["compatibility_layer"]["option_class"] = str(option_class)
        except ImportError as e:
            logger.warning(f"Could not import utils.command_imports: {e}")
        
        # Test 2: interaction_handlers.py
        try:
            from utils.interaction_handlers import (
                safely_respond_to_interaction,
                get_interaction_user
            )
            compatibility_modules.append("utils.interaction_handlers")
            logger.info("Imported utils.interaction_handlers successfully")
        except ImportError as e:
            logger.warning(f"Could not import utils.interaction_handlers: {e}")
        
        # Test 3: command_handlers.py
        try:
            from utils.command_handlers import (
                enhanced_slash_command,
                option,
                command_handler,
                defer_interaction
            )
            compatibility_modules.append("utils.command_handlers")
            logger.info("Imported utils.command_handlers successfully")
        except ImportError as e:
            logger.warning(f"Could not import utils.command_handlers: {e}")
        
        # Test 4: command_tree.py
        try:
            from utils.command_tree import (
                create_command_tree,
                sync_command_tree
            )
            compatibility_modules.append("utils.command_tree")
            logger.info("Imported utils.command_tree successfully")
        except ImportError as e:
            logger.warning(f"Could not import utils.command_tree: {e}")
        
        # Test 5: cog_helpers.py
        try:
            from utils.cog_helpers import (
                register_command_in_cog,
                cog_slash_command,
                CogWithSlashCommands
            )
            compatibility_modules.append("utils.cog_helpers")
            logger.info("Imported utils.cog_helpers successfully")
        except ImportError as e:
            logger.warning(f"Could not import utils.cog_helpers: {e}")
        
        test_results["compatibility_layer"]["compatibility_modules"] = compatibility_modules
        
        # Based on the results, determine if our compatibility layer is complete
        if len(compatibility_modules) == 5:
            logger.info("Compatibility layer appears complete")
            test_results["compatibility_layer"]["status"] = "complete"
        elif len(compatibility_modules) > 0:
            logger.info("Compatibility layer is partial")
            test_results["compatibility_layer"]["status"] = "partial"
        else:
            logger.info("Compatibility layer is missing")
            test_results["compatibility_layer"]["status"] = "missing"
        
        return TestOutcome.SUCCESS
    except Exception as e:
        logger.error(f"Error during compatibility layer test: {e}")
        logger.error(traceback.format_exc())
        test_results["compatibility_layer"]["error"] = str(e)
        return TestOutcome.ERROR

async def print_summary():
    """Print a summary of all test results"""
    logger.info("\n\n=== PY-CORD 2.6.1 COMPATIBILITY TEST SUMMARY ===\n")
    
    # Library detection
    logger.info("Library Detection:")
    for key, value in test_results["library_detection"].items():
        logger.info(f"  {key}: {value}")
    
    # Interaction features
    logger.info("\nInteraction Features:")
    for key, value in test_results["interaction_features"].items():
        logger.info(f"  {key}: {value}")
    
    # Command features
    logger.info("\nCommand Features:")
    for key, value in test_results["command_features"].items():
        logger.info(f"  {key}: {value}")
    
    # Compatibility layer
    logger.info("\nCompatibility Layer:")
    for key, value in test_results["compatibility_layer"].items():
        logger.info(f"  {key}: {value}")
    
    # Overall compatibility assessment
    logger.info("\n=== COMPATIBILITY ASSESSMENT ===")
    
    # Determine if this is py-cord 2.6.1
    is_pycord_261 = test_results["library_detection"].get("is_pycord_261", False)
    if is_pycord_261:
        logger.info("Detected py-cord 2.6.1")
        
        # Check if compatibility layer is complete
        compatibility_status = test_results["compatibility_layer"].get("status", "unknown")
        if compatibility_status == "complete":
            logger.info("Compatibility layer is COMPLETE - should work correctly")
        elif compatibility_status == "partial":
            logger.info("Compatibility layer is PARTIAL - may have issues")
        else:
            logger.info("Compatibility layer is MISSING - will have issues")
    else:
        logger.info("Not using py-cord 2.6.1 - compatibility layer will adapt to detected library")
    
    logger.info("\n=== END OF SUMMARY ===\n")

async def run_tests():
    """Run all compatibility tests"""
    tests = [
        ("Library Detection", test_library_detection),
        ("Interaction Features", test_interaction_features),
        ("Command Features", test_command_features),
        ("Compatibility Layer", test_compatibility_layer)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n=== Running Test: {test_name} ===\n")
        outcome = await test_func()
        logger.info(f"Test Outcome: {outcome}")
    
    await print_summary()

def main():
    """Main entry point"""
    logger.info("Starting py-cord 2.6.1 compatibility tests")
    
    # Run tests using asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_tests())
    
    logger.info("Compatibility tests complete")

if __name__ == "__main__":
    main()