"""
Compatibility Verification Tool

This script checks for compatibility issues between the current environment and
the required dependencies for the Tower of Temptation Discord bot.
"""

import importlib
import inspect
import logging
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Compatibility verification results
class VerificationResult:
    def __init__(self):
        self.discord_version = None
        self.pymongo_version = None
        self.motor_version = None
        self.discord_compatibility = False
        self.mongodb_compatibility = False
        self.command_compatibility = False
        self.async_compatibility = False
        self.event_compatibility = False
        self.overall_compatibility = False
        self.issues = []
        self.warnings = []
        self.recommendations = []
        
    def add_issue(self, component: str, issue: str, severity: str = "error"):
        """Add an issue to the verification result."""
        self.issues.append({
            "component": component,
            "issue": issue,
            "severity": severity
        })
        
    def add_warning(self, component: str, warning: str):
        """Add a warning to the verification result."""
        self.warnings.append({
            "component": component,
            "warning": warning
        })
        
    def add_recommendation(self, component: str, recommendation: str):
        """Add a recommendation to the verification result."""
        self.recommendations.append({
            "component": component,
            "recommendation": recommendation
        })
        
    def is_compatible(self) -> bool:
        """Check if the environment is compatible."""
        return (
            self.discord_compatibility and
            self.mongodb_compatibility and
            self.command_compatibility and
            self.async_compatibility and
            self.event_compatibility and
            len(self.issues) == 0
        )
        
    def print_report(self):
        """Print a detailed compatibility report."""
        print("\n" + "=" * 80)
        print("COMPATIBILITY VERIFICATION REPORT")
        print("=" * 80)
        
        print("\nEnvironment:")
        print(f"  Discord Version: {self.discord_version}")
        print(f"  PyMongo Version: {self.pymongo_version}")
        print(f"  Motor Version: {self.motor_version}")
        
        print("\nCompatibility Status:")
        print(f"  Discord API: {'✅' if self.discord_compatibility else '❌'}")
        print(f"  MongoDB: {'✅' if self.mongodb_compatibility else '❌'}")
        print(f"  Command System: {'✅' if self.command_compatibility else '❌'}")
        print(f"  Async/Await: {'✅' if self.async_compatibility else '❌'}")
        print(f"  Event System: {'✅' if self.event_compatibility else '❌'}")
        print(f"\nOverall Compatibility: {'✅' if self.is_compatible() else '❌'}")
        
        if self.issues:
            print("\nIssues:")
            for issue in self.issues:
                severity_mark = "❌" if issue["severity"] == "error" else "⚠️"
                print(f"  {severity_mark} [{issue['component']}] {issue['issue']}")
        
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠️ [{warning['component']}] {warning['warning']}")
        
        if self.recommendations:
            print("\nRecommendations:")
            for rec in self.recommendations:
                print(f"  💡 [{rec['component']}] {rec['recommendation']}")
                
        print("\n" + "=" * 80)

def check_discord_compatibility(result: VerificationResult):
    """Check Discord API compatibility."""
    try:
        import discord
        from discord.ext import commands
        
        result.discord_version = discord.__version__
        
        # Check if we're using py-cord
        using_pycord = hasattr(discord, "VoiceProtocol")
        if not using_pycord:
            result.add_issue("Discord", "Not using py-cord library")
            return False
            
        # Check py-cord version
        version_parts = discord.__version__.split('.')
        if len(version_parts) >= 3:
            major, minor, patch = map(int, version_parts[:3])
            if major < 2 or (major == 2 and minor < 6) or (major == 2 and minor == 6 and patch < 1):
                result.add_issue("Discord", f"py-cord version {discord.__version__} is older than required 2.6.1")
                return False
                
        # Check for compatibility modules
        try:
            from utils import discord_compat
            from utils import attribute_access
            from utils import interaction_handlers
            
            # Check specific functionality
            has_attr_access = hasattr(attribute_access, "safe_server_getattr")
            has_hybrid_send = hasattr(interaction_handlers, "hybrid_send")
            
            if not has_attr_access or not has_hybrid_send:
                result.add_issue("Discord", "Missing required compatibility functions")
                return False
                
        except ImportError as e:
            result.add_issue("Discord", f"Missing compatibility modules: {e}")
            return False
            
        result.discord_compatibility = True
        return True
        
    except ImportError as e:
        result.add_issue("Discord", f"Failed to import Discord libraries: {e}")
        return False
        
def check_mongodb_compatibility(result: VerificationResult):
    """Check MongoDB compatibility."""
    try:
        import pymongo
        import motor.motor_asyncio
        
        result.pymongo_version = pymongo.__version__
        result.motor_version = motor.__version__
        
        # Check pymongo version
        pymongo_version_parts = pymongo.__version__.split('.')
        if len(pymongo_version_parts) >= 2:
            major, minor = map(int, pymongo_version_parts[:2])
            if major < 4 or (major == 4 and minor < 3):
                result.add_issue("MongoDB", f"pymongo version {pymongo.__version__} is older than required 4.3.0")
                return False
                
        # Check for compatibility modules
        try:
            from utils import safe_mongodb
            from utils import mongo_compat
            
            # Check specific functionality
            has_safe_result = hasattr(safe_mongodb, "SafeMongoDBResult")
            has_serialize = hasattr(mongo_compat, "serialize_document")
            
            if not has_safe_result or not has_serialize:
                result.add_issue("MongoDB", "Missing required compatibility functions")
                return False
                
        except ImportError as e:
            result.add_issue("MongoDB", f"Missing compatibility modules: {e}")
            return False
            
        result.mongodb_compatibility = True
        return True
        
    except ImportError as e:
        result.add_issue("MongoDB", f"Failed to import MongoDB libraries: {e}")
        return False
        
def check_command_system_compatibility(result: VerificationResult):
    """Check command system compatibility."""
    try:
        # Check for compatibility modules
        from utils import command_handlers
        from utils import command_parameter_builder
        
        # Check specific functionality
        has_enhanced_command = hasattr(command_handlers, "EnhancedSlashCommand")
        has_command_builder = hasattr(command_parameter_builder, "CommandBuilder")
        
        if not has_enhanced_command or not has_command_builder:
            result.add_issue("Command System", "Missing required compatibility classes")
            return False
            
        result.command_compatibility = True
        return True
        
    except ImportError as e:
        result.add_issue("Command System", f"Missing compatibility modules: {e}")
        return False
        
def check_async_compatibility(result: VerificationResult):
    """Check async/await and type safety compatibility."""
    try:
        # Check for compatibility modules
        from utils import async_helpers
        from utils import type_safety
        
        # Check specific functionality
        has_ensure_async = hasattr(async_helpers, "ensure_async")
        has_safe_cast = hasattr(type_safety, "safe_cast")
        
        if not has_ensure_async or not has_safe_cast:
            result.add_issue("Async/Type", "Missing required compatibility functions")
            return False
            
        result.async_compatibility = True
        return True
        
    except ImportError as e:
        result.add_issue("Async/Type", f"Missing compatibility modules: {e}")
        return False
        
def check_event_system_compatibility(result: VerificationResult):
    """Check event system and intent compatibility."""
    try:
        # Check for compatibility modules
        from utils import event_helpers
        from utils import intent_helpers
        from utils import permission_helpers
        
        # Check specific functionality
        has_compatible_bot = hasattr(event_helpers, "CompatibleBot")
        has_default_intents = hasattr(intent_helpers, "get_default_intents")
        has_permissions = hasattr(permission_helpers, "has_permission")
        
        if not has_compatible_bot or not has_default_intents or not has_permissions:
            result.add_issue("Event System", "Missing required compatibility classes")
            return False
            
        result.event_compatibility = True
        return True
        
    except ImportError as e:
        result.add_issue("Event System", f"Missing compatibility modules: {e}")
        return False

def verify_compatibility() -> VerificationResult:
    """Verify compatibility for all components."""
    result = VerificationResult()
    
    # Check each component
    check_discord_compatibility(result)
    check_mongodb_compatibility(result)
    check_command_system_compatibility(result)
    check_async_compatibility(result)
    check_event_system_compatibility(result)
    
    # Check for LSP errors in key files
    try:
        import importlib.util
        
        # List of modules to check
        modules_to_check = [
            "utils.discord_compat",
            "utils.attribute_access",
            "utils.interaction_handlers",
            "utils.command_handlers",
            "utils.command_parameter_builder",
            "utils.safe_mongodb",
            "utils.mongo_compat",
            "utils.async_helpers",
            "utils.type_safety",
            "utils.event_helpers",
            "utils.intent_helpers",
            "utils.permission_helpers"
        ]
        
        for module_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                # If we can import it, it's good
            except ImportError as e:
                # This is an issue with the module
                result.add_issue("Import", f"Module {module_name} failed to import: {e}")
            except Exception as e:
                # This is likely an LSP error
                result.add_issue("LSP", f"Module {module_name} has runtime errors: {e}")
    except Exception as e:
        result.add_warning("LSP", f"Failed to check for LSP errors: {e}")
    
    # Set overall compatibility
    result.overall_compatibility = result.is_compatible()
    
    # Add recommendations
    if not result.discord_compatibility:
        result.add_recommendation(
            "Discord",
            "Install py-cord 2.6.1 with 'pip install py-cord==2.6.1'"
        )
        
    if not result.mongodb_compatibility:
        result.add_recommendation(
            "MongoDB",
            "Install pymongo 4.6.2 and motor 3.4.0 with 'pip install pymongo==4.6.2 motor==3.4.0'"
        )
        
    if not result.command_compatibility or not result.async_compatibility or not result.event_compatibility:
        result.add_recommendation(
            "Modules",
            "Ensure all compatibility modules are properly installed and importable"
        )
    
    return result

if __name__ == "__main__":
    print("Running compatibility verification...")
    result = verify_compatibility()
    result.print_report()
    
    if not result.is_compatible():
        sys.exit(1)
    else:
        print("All compatibility checks passed!")
        sys.exit(0)