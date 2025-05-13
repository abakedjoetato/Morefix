#!/usr/bin/env python3
"""
Cog Patching Script for Tower of Temptation Discord Bot

This script automatically patches cogs to work with py-cord 2.6.1 by replacing
Discord app_commands imports with our compatibility layer.
"""

import os
import re
import glob
import logging
import sys
import shutil
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("cog_patcher")

# Patterns to replace
PATTERNS = [
    # Replace direct app_commands imports
    (r'from discord import app_commands', 'from utils.discord_patches import app_commands'),
    (r'import discord.app_commands', 'from utils.discord_patches import app_commands'),
    (r'from discord.app_commands import', 'from utils.discord_patches import'),
    
    # Compatibility for py-cord style commands
    (r'@app_commands\.command\(', '@commands.slash_command('),
    
    # Fix for Choice imports
    (r'app_commands\.Choice', 'utils.discord_patches.app_commands.Choice'),
]

def patch_file(file_path: str) -> Tuple[bool, int]:
    """
    Patch a single file with compatibility fixes
    
    Args:
        file_path: Path to the file to patch
        
    Returns:
        Tuple of (success, number of replacements)
    """
    try:
        # Read the file contents
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Make a backup just in case
        backup_path = f"{file_path}.bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Track number of replacements
        total_replacements = 0
        
        # Apply all patterns
        for pattern, replacement in PATTERNS:
            # Count occurrences for reporting
            matches = re.findall(pattern, content)
            count = len(matches)
            total_replacements += count
            
            # Apply replacement
            if count > 0:
                content = re.sub(pattern, replacement, content)
                logger.info(f"  - Replaced {count} occurrences of '{pattern}' with '{replacement}'")
        
        # Write the patched content back to the file
        if total_replacements > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, total_replacements
        else:
            # No replacements needed, clean up backup
            os.remove(backup_path)
            return False, 0
            
    except Exception as e:
        logger.error(f"Error patching file {file_path}: {e}")
        return False, 0

def patch_cogs(cogs_dir: str = "cogs") -> List[str]:
    """
    Patch all cogs in the cogs directory
    
    Args:
        cogs_dir: Directory containing cogs
        
    Returns:
        List of patched files
    """
    # Find all Python files in the cogs directory
    cog_files = glob.glob(os.path.join(cogs_dir, "*.py"))
    
    # Track patched files
    patched_files = []
    
    # Patch each file
    for file_path in cog_files:
        logger.info(f"Patching file: {file_path}")
        
        # Apply patches
        success, replacements = patch_file(file_path)
        
        if success:
            patched_files.append(file_path)
            logger.info(f"  Successfully patched with {replacements} replacements")
        else:
            logger.info(f"  No patches needed")
    
    return patched_files

if __name__ == "__main__":
    logger.info("Starting cog patching process...")
    
    # Patch all cogs
    patched_files = patch_cogs()
    
    # Report results
    if patched_files:
        logger.info(f"Successfully patched {len(patched_files)} files:")
        for file in patched_files:
            logger.info(f"  - {file}")
    else:
        logger.info("No files needed patching")
        
    logger.info("Patching process complete")