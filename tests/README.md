# Tower of Temptation Discord Bot Test Suite

This directory contains comprehensive test infrastructure and test cases for the Tower of Temptation PvP Statistics Bot.

## Test Infrastructure

The test infrastructure consists of several key components:

1. **Discord Mocks** (`discord_mocks.py`): Mock implementations of Discord objects (users, guilds, channels, interactions, etc.) for testing without an actual Discord connection.

2. **Test Fixtures** (`test_fixtures.py`): Database fixtures and mock database implementation for testing without a real MongoDB connection.

3. **Command Tester** (`command_tester.py`): Framework for testing bot commands with validation and automated execution.

4. **Test Runner** (`run_tests.py`): Command-line interface for running tests with various options.

## Test Suites

Test suites are organized by functionality in the `test_suites` directory:

- **SFTP Commands** (`sftp_commands.py`): Tests for SFTP integration commands.
- **Error Handling** (`error_handling.py`): Tests for error handling and telemetry.
- Additional test suites can be added to cover more functionality.

## Running Tests

To run tests, use the `run_tests.py` script:

```
# Run all tests
python -m tests.run_tests --all

# Run specific test suites
python -m tests.run_tests --sftp --error

# Run custom test suite
python -m tests.run_tests --suite my_custom_suite

# Save results to file
python -m tests.run_tests --all --output results.json
```

## Creating New Test Suites

To create a new test suite:

1. Create a new Python file in the `test_suites` directory.
2. Define a `create_test_suite()` function that returns a `CommandTestSuite` instance.
3. Add test cases using `create_slash_command_test()`, `create_prefix_command_test()`, etc.
4. Add validators to verify command behavior.

Example:

```python
from tests.command_tester import (
    CommandTestSuite, ResponseValidator,
    create_slash_command_test
)

def create_test_suite():
    suite = CommandTestSuite("My Feature")
    
    # Add test case
    suite.add_test(create_slash_command_test(
        command_name="my_command",
        options={"option1": "value1"},
        validators=[
            ResponseValidator(
                embed_title="Expected Title",
                content_contains=["expected", "content"]
            )
        ]
    ))
    
    return suite
```

## Validators

The test framework includes several validators for verifying command behavior:

- **ResponseValidator**: Checks command responses (content, embeds, etc.).
- **ExceptionValidator**: Verifies expected exceptions.
- **StateValidator**: Validates database or bot state after command execution.

Custom validators can be created by extending the `CommandValidator` base class.

## Continuous Integration

These tests can be integrated into a CI/CD pipeline to automatically verify bot functionality before deployment.

## Further Reading

For more details on the testing framework, see the documentation in each module:

- `discord_mocks.py`: Mock Discord objects
- `test_fixtures.py`: Database fixtures
- `command_tester.py`: Command testing framework
- `run_tests.py`: Test runner