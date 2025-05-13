"""
Compatibility Layer Application Tool

This script helps apply the compatibility layers to existing codebase files,
replacing imports and making necessary adjustments to use the compatibility layers.
"""

import os
import re
import sys
from typing import List, Dict, Tuple, Set

# Patterns to search for
PATTERNS = {
    # Discord imports
    r"import discord": "from utils.discord_compat import discord",
    r"from discord\.ext import commands": "from utils.discord_compat import commands",
    r"from discord import app_commands": "from utils.discord_compat import app_commands",
    
    # MongoDB imports
    r"from pymongo import MongoClient": "from motor.motor_asyncio import AsyncIOMotorClient as MongoClient",
    r"from motor\.motor_asyncio import AsyncIOMotorClient": "from motor.motor_asyncio import AsyncIOMotorClient",
    
    # Direct attribute access
    r"(server|guild)\.name": "safe_server_getattr(\\1, 'name')",
    r"(server|guild)\.id": "safe_server_getattr(\\1, 'id')",
    r"member\.id": "safe_member_getattr(member, 'id')",
    r"channel\.name": "safe_channel_getattr(channel, 'name')",
    r"role\.id": "safe_role_getattr(role, 'id')",
    r"message\.content": "safe_message_getattr(message, 'content')",
    
    # MongoDB result access
    r"result\.acknowledged": "SafeMongoDBResult(result).acknowledged",
    r"result\.inserted_id": "SafeMongoDBResult(result).inserted_id",
    r"result\.modified_count": "SafeMongoDBResult(result).modified_count",
    r"result\.matched_count": "SafeMongoDBResult(result).matched_count",
    r"result\.deleted_count": "SafeMongoDBResult(result).deleted_count",
    r"result\.upserted_id": "SafeMongoDBResult(result).upserted_id",
}

# Required imports to add
REQUIRED_IMPORTS = {
    # For server attribute access
    "safe_server_getattr": "from utils.attribute_access import safe_server_getattr",
    "safe_member_getattr": "from utils.attribute_access import safe_member_getattr",
    "safe_channel_getattr": "from utils.attribute_access import safe_channel_getattr",
    "safe_role_getattr": "from utils.attribute_access import safe_role_getattr",
    "safe_message_getattr": "from utils.attribute_access import safe_message_getattr",
    
    # For MongoDB result access
    "SafeMongoDBResult": "from utils.safe_mongodb import SafeMongoDBResult",
    
    # For interaction handling
    "safely_respond_to_interaction": "from utils.interaction_handlers import safely_respond_to_interaction",
    "hybrid_send": "from utils.interaction_handlers import hybrid_send",
    
    # For async helpers
    "safe_gather": "from utils.async_helpers import safe_gather",
    "ensure_async": "from utils.async_helpers import ensure_async",
    
    # For type safety
    "safe_str": "from utils.type_safety import safe_str",
    "safe_int": "from utils.type_safety import safe_int",
}

def process_file(file_path: str, dry_run: bool = False) -> Tuple[int, Set[str]]:
    """
    Process a file to apply compatibility layers.
    
    Args:
        file_path: Path to the file
        dry_run: Whether to perform a dry run (no changes)
        
    Returns:
        Tuple of (number of changes, set of required imports)
    """
    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Track changes and required imports
    changes = 0
    needed_imports = set()
    
    # Apply patterns
    for pattern, replacement in PATTERNS.items():
        # Compile the pattern
        compiled = re.compile(pattern)
        
        # Find matches
        matches = compiled.findall(content)
        if matches:
            # Add to required imports based on replacement
            for keyword in ["safe_server_getattr", "safe_member_getattr", "safe_channel_getattr",
                           "safe_role_getattr", "safe_message_getattr", "SafeMongoDBResult"]:
                if keyword in replacement:
                    needed_imports.add(keyword)
            
            # Apply replacement
            new_content = compiled.sub(replacement, content)
            
            # Count changes
            if new_content != content:
                changes += len(matches)
                content = new_content
    
    # Write the file if changes were made
    if changes > 0 and not dry_run:
        # Add required imports if needed
        if needed_imports:
            import_lines = []
            for keyword in needed_imports:
                if keyword in REQUIRED_IMPORTS:
                    import_lines.append(REQUIRED_IMPORTS[keyword])
            
            # Add imports after existing imports
            if import_lines:
                # Find the last import line
                import_match = re.search(r"^(?:import|from) .*$", content, re.MULTILINE)
                if import_match:
                    last_import_end = import_match.end()
                    # Add imports after the last import
                    new_content = (
                        content[:last_import_end] + 
                        "\n" + "\n".join(import_lines) + 
                        content[last_import_end:]
                    )
                    content = new_content
                else:
                    # Add imports at the beginning of the file
                    content = "\n".join(import_lines) + "\n\n" + content
        
        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    return changes, needed_imports

def process_directory(directory: str, extensions: List[str] = [".py"], dry_run: bool = False) -> Dict[str, int]:
    """
    Process a directory to apply compatibility layers.
    
    Args:
        directory: Directory to process
        extensions: File extensions to process
        dry_run: Whether to perform a dry run (no changes)
        
    Returns:
        Dictionary of file paths to number of changes
    """
    results = {}
    
    # Walk the directory
    for root, _, files in os.walk(directory):
        for file in files:
            # Check file extension
            if any(file.endswith(ext) for ext in extensions):
                # Get file path
                file_path = os.path.join(root, file)
                
                # Process the file
                changes, needed_imports = process_file(file_path, dry_run)
                
                # Add to results
                if changes > 0:
                    results[file_path] = changes
                    print(f"{file_path}: {changes} changes, needed imports: {needed_imports}")
    
    return results

def main():
    """Main function."""
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python apply_compatibility.py <directory> [--dry-run]")
        sys.exit(1)
    
    # Get arguments
    directory = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    # Check if directory exists
    if not os.path.isdir(directory):
        print(f"Directory {directory} does not exist")
        sys.exit(1)
    
    # Process the directory
    print(f"Processing directory {directory}{'(dry run)' if dry_run else ''}...")
    results = process_directory(directory, dry_run=dry_run)
    
    # Print results
    print(f"\nProcessed {len(results)} files with changes")
    total_changes = sum(results.values())
    print(f"Total changes: {total_changes}")
    
    # Print most changed files
    if results:
        print("\nMost changed files:")
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        for file_path, changes in sorted_results[:10]:
            print(f"  {file_path}: {changes} changes")

if __name__ == "__main__":
    main()