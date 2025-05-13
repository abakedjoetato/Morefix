"""
Command Tester for Tower of Temptation PvP Statistics Bot

This module provides a framework for testing commands:
1. Automated command execution
2. Response validation
3. State validation
4. Exception handling verification

The framework allows for comprehensive testing of all bot commands
without requiring a live Discord connection.
"""
import asyncio
import inspect
import unittest
import datetime
import logging
import traceback
import json
import os
import sys
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
from unittest.mock import MagicMock, AsyncMock, patch

# Import mock utilities
from tests.discord_mocks import (
    MockUser, MockGuild, MockChannel, MockMessage, 
    MockInteraction, MockContext, MockApplicationContext,
    create_mock_user, create_mock_guild, create_mock_interaction, 
    create_mock_context, create_mock_application_context
)

# Import test fixtures
from tests.test_fixtures import setup_test_database

# Setup logging
logger = logging.getLogger("command_tester")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Command test exceptions
class CommandTestError(Exception):
    """Base exception for command testing errors"""
    pass

class CommandExecutionError(CommandTestError):
    """Raised when a command fails to execute"""
    pass

class CommandValidationError(CommandTestError):
    """Raised when command validation fails"""
    pass

class CommandEnvironmentError(CommandTestError):
    """Raised when the command environment cannot be set up"""
    pass

# Test result class
class CommandTestResult:
    """Results of a command test execution"""
    
    def __init__(self, 
                 command_name: str, 
                 success: bool = True, 
                 execution_time: float = 0.0,
                 response=None,
                 exception=None,
                 context=None):
        """Initialize test result
        
        Args:
            command_name: Name of the command tested
            success: Whether the test passed
            execution_time: Time taken to execute the command in seconds
            response: Command response or returned value
            exception: Exception raised during execution (if any)
            context: Command context object
        """
        self.command_name = command_name
        self.success = success
        self.execution_time = execution_time
        self.response = response
        self.exception = exception
        self.context = context
        self.timestamp = datetime.datetime.now()
        self.validation_results = []
    
    def add_validation_result(self, validator_name: str, passed: bool, message: str = None):
        """Add a validation result
        
        Args:
            validator_name: Name of the validator
            passed: Whether validation passed
            message: Optional message with details
        """
        self.validation_results.append({
            "validator": validator_name,
            "passed": passed,
            "message": message
        })
    
    def to_dict(self):
        """Convert test result to dictionary
        
        Returns:
            Dictionary representation of test result
        """
        return {
            "command_name": self.command_name,
            "success": self.success,
            "execution_time": self.execution_time,
            "response": str(self.response) if self.response is not None else None,
            "exception": str(self.exception) if self.exception is not None else None,
            "timestamp": self.timestamp.isoformat(),
            "validation_results": self.validation_results
        }
    
    def __str__(self):
        """String representation of test result
        
        Returns:
            String with test result details
        """
        result = f"Test for '{self.command_name}': "
        result += "PASSED" if self.success else "FAILED"
        result += f" ({self.execution_time:.4f}s)"
        
        if self.exception:
            result += f"\nException: {type(self.exception).__name__}: {self.exception}"
        
        if self.validation_results:
            result += "\nValidation Results:"
            for vr in self.validation_results:
                status = "PASSED" if vr["passed"] else "FAILED"
                result += f"\n - {vr['validator']}: {status}"
                if vr["message"]:
                    result += f" ({vr['message']})"
        
        return result

# Command validator base class
class CommandValidator:
    """Base class for command validators"""
    
    def __init__(self, name: str = None):
        """Initialize validator
        
        Args:
            name: Validator name (defaults to class name)
        """
        self.name = name or self.__class__.__name__
    
    async def validate(self, result: CommandTestResult, test_case: "CommandTestCase") -> Dict[str, Any]:
        """Validate command execution
        
        Args:
            result: Command test result to validate
            test_case: The test case being executed
            
        Returns:
            Dictionary with validation results:
            {
                "passed": bool,
                "message": Optional explanation
            }
        """
        raise NotImplementedError("Subclasses must implement validate()")

# Common validators
class ResponseValidator(CommandValidator):
    """Validates command response"""
    
    def __init__(self, 
                 expected_type=None, 
                 expected_content=None,
                 content_contains=None,
                 embed_title=None,
                 embed_description=None,
                 embed_field_names=None):
        """Initialize response validator
        
        Args:
            expected_type: Expected type of response
            expected_content: Expected content (exact match)
            content_contains: List of strings that should be in content
            embed_title: Expected embed title
            embed_description: Expected embed description 
            embed_field_names: Expected embed field names
        """
        super().__init__("ResponseValidator")
        self.expected_type = expected_type
        self.expected_content = expected_content
        self.content_contains = content_contains or []
        self.embed_title = embed_title
        self.embed_description = embed_description
        self.embed_field_names = embed_field_names
    
    async def validate(self, result: CommandTestResult, test_case: "CommandTestCase") -> Dict[str, Any]:
        """Validate command response
        
        Args:
            result: Command test result
            test_case: Test case
            
        Returns:
            Validation results
        """
        # Initialize result
        validation = {"passed": True, "message": None}
        messages = []
        
        # Check for response existence
        if result.response is None:
            if self.expected_type is None:
                return validation  # No response expected
            
            validation["passed"] = False
            validation["message"] = "No response received"
            return validation
        
        # Type validation
        if self.expected_type and not isinstance(result.response, self.expected_type):
            validation["passed"] = False
            messages.append(f"Expected response type {self.expected_type.__name__}, got {type(result.response).__name__}")
        
        # Get content based on response type
        content = None
        embed = None
        
        if hasattr(result.response, "content"):
            content = result.response.content
        elif isinstance(result.response, str):
            content = result.response
        
        if hasattr(result.response, "embeds") and result.response.embeds:
            embed = result.response.embeds[0]
        
        # Content validation
        if self.expected_content is not None and content != self.expected_content:
            validation["passed"] = False
            messages.append(f"Expected content '{self.expected_content}', got '{content}'")
        
        # Content contains validation
        if content and self.content_contains:
            for text in self.content_contains:
                if text not in content:
                    validation["passed"] = False
                    messages.append(f"Content does not contain '{text}'")
        
        # Embed validation
        if embed:
            if self.embed_title and embed.title != self.embed_title:
                validation["passed"] = False
                messages.append(f"Expected embed title '{self.embed_title}', got '{embed.title}'")
            
            if self.embed_description and embed.description != self.embed_description:
                validation["passed"] = False
                messages.append(f"Expected embed description '{self.embed_description}', got '{embed.description}'")
            
            if self.embed_field_names:
                actual_fields = [f.name for f in embed.fields]
                for field_name in self.embed_field_names:
                    if field_name not in actual_fields:
                        validation["passed"] = False
                        messages.append(f"Embed missing field '{field_name}'")
        elif any([self.embed_title, self.embed_description, self.embed_field_names]):
            validation["passed"] = False
            messages.append("Expected embed but none found")
        
        # Set message if validation failed
        if not validation["passed"]:
            validation["message"] = ", ".join(messages)
        
        return validation

class ExceptionValidator(CommandValidator):
    """Validates expected exceptions"""
    
    def __init__(self, expected_exception=None, expected_message=None):
        """Initialize exception validator
        
        Args:
            expected_exception: Expected exception type (or None if no exception expected)
            expected_message: Expected exception message
        """
        super().__init__("ExceptionValidator")
        self.expected_exception = expected_exception
        self.expected_message = expected_message
    
    async def validate(self, result: CommandTestResult, test_case: "CommandTestCase") -> Dict[str, Any]:
        """Validate command exceptions
        
        Args:
            result: Command test result
            test_case: Test case
            
        Returns:
            Validation results
        """
        # If no exception expected
        if self.expected_exception is None:
            if result.exception is None:
                return {"passed": True, "message": None}
            else:
                return {
                    "passed": False, 
                    "message": f"Unexpected exception: {type(result.exception).__name__}: {result.exception}"
                }
        
        # If exception expected but none raised
        if result.exception is None:
            return {
                "passed": False,
                "message": f"Expected {self.expected_exception.__name__} exception, but none raised"
            }
        
        # Check exception type
        if not isinstance(result.exception, self.expected_exception):
            return {
                "passed": False,
                "message": f"Expected {self.expected_exception.__name__}, got {type(result.exception).__name__}"
            }
        
        # Check exception message if specified
        if self.expected_message and self.expected_message not in str(result.exception):
            return {
                "passed": False,
                "message": f"Expected message '{self.expected_message}', got '{str(result.exception)}'"
            }
        
        return {"passed": True, "message": None}

class StateValidator(CommandValidator):
    """Validates bot or database state after command execution"""
    
    def __init__(self, validation_func=None, name=None):
        """Initialize state validator
        
        Args:
            validation_func: Function to validate state
            name: Validator name
        """
        super().__init__(name or "StateValidator")
        self.validation_func = validation_func
    
    async def validate(self, result: CommandTestResult, test_case: "CommandTestCase") -> Dict[str, Any]:
        """Validate state after command execution
        
        Args:
            result: Command test result
            test_case: Test case
            
        Returns:
            Validation results
        """
        if not self.validation_func:
            return {"passed": True, "message": "No validation function provided"}
        
        try:
            # Call validation function
            validation_result = await self.validation_func(test_case.bot, test_case.db, result)
            
            if isinstance(validation_result, bool):
                return {
                    "passed": validation_result,
                    "message": None if validation_result else "State validation failed"
                }
            elif isinstance(validation_result, dict):
                return validation_result
            else:
                return {
                    "passed": bool(validation_result),
                    "message": str(validation_result) if not bool(validation_result) else None
                }
        except Exception as e:
            return {
                "passed": False,
                "message": f"Validation function raised exception: {type(e).__name__}: {e}"
            }

# Command test case
class CommandTestCase:
    """Test case for a single command"""
    
    def __init__(self, 
                 command_name: str, 
                 command_type: str = "slash",
                 guild_id: str = None,
                 user_id: str = None,
                 channel_id: str = None,
                 options: Dict[str, Any] = None,
                 validators: List[CommandValidator] = None):
        """Initialize command test case
        
        Args:
            command_name: Name of the command to test
            command_type: Type of command ("slash", "prefix", "component")
            guild_id: Guild ID for the command context
            user_id: User ID for the command context
            channel_id: Channel ID for the command context
            options: Command options or arguments
            validators: List of validators to run after execution
        """
        self.command_name = command_name
        self.command_type = command_type
        self.guild_id = guild_id
        self.user_id = user_id
        self.channel_id = channel_id
        self.options = options or {}
        self.validators = validators or []
        
        # Will be set during test execution
        self.bot = None
        self.db = None
        self.guild = None
        self.user = None
        self.channel = None
        self.context = None
    
    async def setup(self, bot, db):
        """Set up test environment
        
        Args:
            bot: Bot instance
            db: Database instance
        """
        self.bot = bot
        self.db = db
        
        # Create mock guild
        self.guild = create_mock_guild(id=self.guild_id or "100000000000000000")
        
        # Create mock user
        self.user = create_mock_user(id=self.user_id or "200000000000000000")
        
        # Create mock channel
        self.channel = MockChannel(
            id=self.channel_id or "300000000000000000",
            guild=self.guild
        )
        
        # Add user to guild
        self.guild.add_member(self.user)
        
        # Add channel to guild
        self.guild.add_channel(self.channel)
        
        # Create context based on command type
        if self.command_type == "slash":
            # Convert options dict to interaction options format
            interaction_options = []
            for name, value in self.options.items():
                option_type = 3  # STRING
                if isinstance(value, bool):
                    option_type = 5  # BOOLEAN
                elif isinstance(value, int):
                    option_type = 4  # INTEGER
                elif isinstance(value, float):
                    option_type = 10  # NUMBER
                
                interaction_options.append({
                    "name": name,
                    "type": option_type,
                    "value": value
                })
            
            # Create interaction
            interaction = create_mock_interaction(
                command_name=self.command_name,
                guild=self.guild,
                user=self.user,
                channel=self.channel,
                options=interaction_options
            )
            
            # Create application context
            self.context = MockApplicationContext(interaction=interaction, bot=self.bot)
        
        elif self.command_type == "prefix":
            # Create message content with prefix and arguments
            content = f"!{self.command_name}"
            
            # Add string arguments
            for name, value in self.options.items():
                content += f" {value}"
            
            # Create message
            message = MockMessage(
                content=content,
                author=self.user,
                channel=self.channel,
                guild=self.guild
            )
            
            # Create context
            self.context = MockContext(
                message=message,
                author=self.user,
                guild=self.guild,
                channel=self.channel,
                bot=self.bot,
                command_name=self.command_name
            )
        
        elif self.command_type == "component":
            # Create interaction with component data
            component_data = {
                "custom_id": self.command_name,
                "component_type": 2,  # BUTTON
                "values": list(self.options.values()) if self.options else []
            }
            
            interaction = create_mock_interaction(
                type=3,  # COMPONENT
                guild=self.guild,
                user=self.user,
                channel=self.channel,
                data=component_data
            )
            
            # Create context
            self.context = interaction
        
        else:
            raise CommandEnvironmentError(f"Unsupported command type: {self.command_type}")
    
    async def execute(self) -> CommandTestResult:
        """Execute command test
        
        Returns:
            CommandTestResult with test results
        """
        if not self.bot or not self.context:
            raise CommandEnvironmentError("Test environment not set up")
        
        # Find command to execute
        command = None
        
        if self.command_type == "slash":
            # Find in application commands
            for cmd in self.bot.application_commands:
                if cmd.name == self.command_name:
                    command = cmd
                    break
            
            # Find in cogs
            if not command:
                for cog in self.bot.cogs.values():
                    for cmd in getattr(cog, "get_application_commands", lambda: [])():
                        if cmd.name == self.command_name:
                            command = cmd
                            break
                    if command:
                        break
        
        elif self.command_type == "prefix":
            # Find in commands
            command = self.bot.get_command(self.command_name)
        
        elif self.command_type == "component":
            # Cannot directly execute component callbacks
            # Instead, we'll simulate by looking for the component handler
            # This is a simplified approach and may need adaptation for real tests
            command = self.command_name  # Just store the name
        
        # Initialize test result
        result = CommandTestResult(
            command_name=self.command_name,
            context=self.context
        )
        
        # Execute command
        start_time = datetime.datetime.now()
        try:
            if self.command_type == "slash":
                if not command:
                    raise CommandExecutionError(f"Slash command '{self.command_name}' not found")
                
                # Execute slash command
                response = await command._invoke(self.context)
                result.response = response or getattr(self.context, "_respond_with", None)
            
            elif self.command_type == "prefix":
                if not command:
                    raise CommandExecutionError(f"Prefix command '{self.command_name}' not found")
                
                # Execute prefix command
                await self.bot.invoke(self.context)
                result.response = self.context.message._state.messages[-1] if self.context.message._state.messages else None
            
            elif self.command_type == "component":
                # Simulate component handler
                # This is simplified and depends on bot implementation
                result.response = await self.bot.process_component(self.context)
            
            # Set success and execution time
            result.success = True
            result.execution_time = (datetime.datetime.now() - start_time).total_seconds()
        
        except Exception as e:
            # Set failure and exception
            result.success = False
            result.exception = e
            result.execution_time = (datetime.datetime.now() - start_time).total_seconds()
        
        # Run validators
        for validator in self.validators:
            validation_result = await validator.validate(result, self)
            result.add_validation_result(
                validator.name,
                validation_result["passed"],
                validation_result["message"]
            )
            
            # Update overall success
            if not validation_result["passed"]:
                result.success = False
        
        return result

# Command test suite
class CommandTestSuite:
    """Collection of command tests"""
    
    def __init__(self, name: str = "Command Test Suite"):
        """Initialize test suite
        
        Args:
            name: Suite name
        """
        self.name = name
        self.tests = []
        self.results = []
        self.setup_functions = []
        self.teardown_functions = []
    
    def add_test(self, test):
        """Add a test to the suite
        
        Args:
            test: CommandTestCase to add
        """
        self.tests.append(test)
    
    def add_setup(self, setup_func):
        """Add a setup function
        
        Args:
            setup_func: Async function to run before tests
        """
        self.setup_functions.append(setup_func)
    
    def add_teardown(self, teardown_func):
        """Add a teardown function
        
        Args:
            teardown_func: Async function to run after tests
        """
        self.teardown_functions.append(teardown_func)
    
    async def run(self, bot=None, db=None):
        """Run all tests in the suite
        
        Args:
            bot: Bot instance to test with
            db: Database instance to test with
            
        Returns:
            List of test results
        """
        # If no bot or db provided, create mocks
        if bot is None:
            bot = MagicMock()
            bot.application_commands = []
            bot.cogs = {}
            bot.get_command = MagicMock(return_value=None)
            bot.invoke = AsyncMock()
            bot.process_component = AsyncMock()
        
        if db is None:
            _, db = await setup_test_database()
        
        # Run setup functions
        for setup_func in self.setup_functions:
            await setup_func(bot, db)
        
        # Run tests
        try:
            for test in self.tests:
                logger.info(f"Running test: {test.command_name}")
                
                try:
                    # Setup test environment
                    await test.setup(bot, db)
                    
                    # Execute test
                    result = await test.execute()
                    
                    # Store result
                    self.results.append(result)
                    
                    # Log result
                    if result.success:
                        logger.info(f"Test passed: {test.command_name}")
                    else:
                        logger.warning(f"Test failed: {test.command_name}")
                        if result.exception:
                            logger.warning(f"Exception: {type(result.exception).__name__}: {result.exception}")
                
                except Exception as e:
                    # Log error
                    logger.error(f"Error running test {test.command_name}: {type(e).__name__}: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Create failure result
                    result = CommandTestResult(
                        command_name=test.command_name,
                        success=False,
                        exception=e
                    )
                    self.results.append(result)
        
        finally:
            # Run teardown functions
            for teardown_func in self.teardown_functions:
                try:
                    await teardown_func(bot, db)
                except Exception as e:
                    logger.error(f"Error in teardown: {type(e).__name__}: {e}")
        
        return self.results
    
    def get_summary(self):
        """Get test summary
        
        Returns:
            Dictionary with summary information
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        
        return {
            "name": self.name,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0
        }
    
    def print_summary(self):
        """Print test summary"""
        summary = self.get_summary()
        
        print(f"\n=== {summary['name']} ===")
        print(f"Total tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass rate: {summary['pass_rate']:.1%}")
        
        if summary['failed'] > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result.success:
                    print(f" - {result.command_name}")
    
    def save_results(self, filename):
        """Save test results to a file
        
        Args:
            filename: File to save to
        """
        data = {
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

# Helper functions for creating tests
def create_slash_command_test(command_name, options=None, validators=None, **kwargs):
    """Create a slash command test case
    
    Args:
        command_name: Command to test
        options: Command options
        validators: Test validators
        **kwargs: Additional arguments for CommandTestCase
        
    Returns:
        CommandTestCase instance
    """
    return CommandTestCase(
        command_name=command_name,
        command_type="slash",
        options=options or {},
        validators=validators or [],
        **kwargs
    )

def create_prefix_command_test(command_name, options=None, validators=None, **kwargs):
    """Create a prefix command test case
    
    Args:
        command_name: Command to test
        options: Command arguments
        validators: Test validators
        **kwargs: Additional arguments for CommandTestCase
        
    Returns:
        CommandTestCase instance
    """
    return CommandTestCase(
        command_name=command_name,
        command_type="prefix",
        options=options or {},
        validators=validators or [],
        **kwargs
    )

def create_component_test(custom_id, values=None, validators=None, **kwargs):
    """Create a component interaction test case
    
    Args:
        custom_id: Component custom ID
        values: Component values
        validators: Test validators
        **kwargs: Additional arguments for CommandTestCase
        
    Returns:
        CommandTestCase instance
    """
    return CommandTestCase(
        command_name=custom_id,
        command_type="component",
        options=values or {},
        validators=validators or [],
        **kwargs
    )

# Main function to run tests
async def run_tests(test_suites, bot=None, db=None):
    """Run multiple test suites
    
    Args:
        test_suites: List of CommandTestSuite instances
        bot: Bot instance to test with
        db: Database instance to test with
        
    Returns:
        Dictionary with all test results
    """
    if bot is None or db is None:
        # Create mock bot and database if not provided
        client, db = await setup_test_database()
        
        if bot is None:
            bot = MagicMock()
            bot.application_commands = []
            bot.cogs = {}
            bot.get_command = MagicMock(return_value=None)
            bot.invoke = AsyncMock()
            bot.process_component = AsyncMock()
            bot.db = db
    
    all_results = {}
    
    for suite in test_suites:
        logger.info(f"Running test suite: {suite.name}")
        results = await suite.run(bot, db)
        suite.print_summary()
        all_results[suite.name] = results
    
    return all_results