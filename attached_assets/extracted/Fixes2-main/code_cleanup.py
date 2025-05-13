#!/usr/bin/env python3
"""
Code Cleanup Script for Tower of Temptation Discord Bot

This script performs codebase cleanup operations:
1. Consistent naming convention enforcement
2. Redundant code removal
3. Dead code detection
4. Import optimization

Run with: python code_cleanup.py [--fix]
"""
import os
import sys
import re
import argparse
import logging
from typing import Dict, List, Set, Tuple, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("code_cleanup.log")
    ]
)
logger = logging.getLogger("code_cleanup")

# Result tracking
CLEANUP_RESULTS = {
    "files_scanned": 0,
    "files_modified": 0,
    "naming_issues": 0,
    "redundant_code": 0,
    "dead_code": 0,
    "import_issues": 0,
    "issues_fixed": 0,
    "all_issues": []
}

# Helper functions
def add_issue(file_path, line_number, issue_type, description, code=None, fix=None):
    """Add an issue to the results
    
    Args:
        file_path: Path to the file with the issue
        line_number: Line number of the issue
        issue_type: Type of issue
        description: Description of the issue
        code: Code snippet with the issue
        fix: Fix for the issue
    """
    issue = {
        "file": file_path,
        "line": line_number,
        "type": issue_type,
        "description": description,
        "code": code,
        "fix": fix
    }
    
    CLEANUP_RESULTS["all_issues"].append(issue)
    
    if issue_type == "naming":
        CLEANUP_RESULTS["naming_issues"] += 1
    elif issue_type == "redundant":
        CLEANUP_RESULTS["redundant_code"] += 1
    elif issue_type == "dead":
        CLEANUP_RESULTS["dead_code"] += 1
    elif issue_type == "import":
        CLEANUP_RESULTS["import_issues"] += 1

def fix_issue(issue, dry_run=True):
    """Fix an issue in the file
    
    Args:
        issue: Issue to fix
        dry_run: Whether to perform a dry run
        
    Returns:
        True if fixed, False otherwise
    """
    if not issue.get("fix"):
        return False
    
    file_path = issue["file"]
    code = issue["code"]
    fix = issue["fix"]
    
    # Read file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return False
    
    # Apply fix
    if code and code in content:
        new_content = content.replace(code, fix)
        
        # Write file if content changed and not dry run
        if new_content != content and not dry_run:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                logger.info(f"Fixed issue in {file_path}")
                CLEANUP_RESULTS["issues_fixed"] += 1
                return True
            except Exception as e:
                logger.error(f"Failed to write file {file_path}: {e}")
                return False
        elif new_content != content:
            logger.info(f"Would fix issue in {file_path} (dry run)")
            return True
    
    return False

def scan_python_file(file_path, fix=False):
    """Scan a Python file for issues
    
    Args:
        file_path: Path to the Python file
        fix: Whether to fix issues
        
    Returns:
        Number of issues found
    """
    logger.info(f"Scanning {file_path}")
    CLEANUP_RESULTS["files_scanned"] += 1
    
    issues_count = 0
    
    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.readlines()
        
        # Check each line
        for i, line in enumerate(content, 1):
            # Check naming conventions
            issues_count += check_naming_conventions(file_path, i, line, fix)
            
            # Check redundant code
            issues_count += check_redundant_code(file_path, i, line, fix)
            
            # Check imports
            issues_count += check_imports(file_path, i, line, fix)
        
        # Check for dead code (requires full file context)
        full_content = "".join(content)
        issues_count += check_dead_code(file_path, full_content, fix)
        
        # Mark file as modified if issues were fixed
        if issues_count > 0 and fix:
            CLEANUP_RESULTS["files_modified"] += 1
        
        return issues_count
    
    except Exception as e:
        logger.error(f"Error scanning {file_path}: {e}")
        return 0

def check_naming_conventions(file_path, line_number, line, fix=False):
    """Check naming conventions in a line
    
    Args:
        file_path: Path to the file
        line_number: Line number
        line: Line content
        fix: Whether to fix issues
        
    Returns:
        Number of issues found
    """
    issues_found = 0
    
    # Check for camelCase variable names
    camel_case_pattern = r'(\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b)\s*='
    for match in re.finditer(camel_case_pattern, line):
        camel_case_var = match.group(1)
        snake_case_var = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', camel_case_var).lower()
        
        # Skip common exceptions
        if camel_case_var in ['fString', 'aPrint', 'aInput']:
            continue
        
        add_issue(
            file_path=file_path,
            line_number=line_number,
            issue_type="naming",
            description=f"Variable '{camel_case_var}' uses camelCase instead of snake_case",
            code=camel_case_var,
            fix=snake_case_var
        )
        issues_found += 1
    
    # Check for non-conforming function names
    func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    for match in re.finditer(func_pattern, line):
        func_name = match.group(1)
        
        # Check for camelCase function names
        if any(c.isupper() for c in func_name) and not func_name.startswith('_'):
            snake_case_func = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', func_name).lower()
            
            add_issue(
                file_path=file_path,
                line_number=line_number,
                issue_type="naming",
                description=f"Function '{func_name}' uses camelCase instead of snake_case",
                code=f"def {func_name}",
                fix=f"def {snake_case_func}"
            )
            issues_found += 1
    
    # Check for non-conforming class names
    class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(class_pattern, line):
        class_name = match.group(1)
        
        # Check for snake_case class names
        if '_' in class_name:
            pascal_case = ''.join(word.capitalize() for word in class_name.split('_'))
            
            add_issue(
                file_path=file_path,
                line_number=line_number,
                issue_type="naming",
                description=f"Class '{class_name}' uses snake_case instead of PascalCase",
                code=f"class {class_name}",
                fix=f"class {pascal_case}"
            )
            issues_found += 1
    
    # Fix issues if requested
    if fix and issues_found > 0:
        for issue in CLEANUP_RESULTS["all_issues"][-issues_found:]:
            fix_issue(issue, dry_run=False)
    
    return issues_found

def check_redundant_code(file_path, line_number, line, fix=False):
    """Check for redundant code in a line
    
    Args:
        file_path: Path to the file
        line_number: Line number
        line: Line content
        fix: Whether to fix issues
        
    Returns:
        Number of issues found
    """
    issues_found = 0
    
    # Check for unnecessary pass statements
    if re.match(r'\s*pass\s*(#.*)?$', line) and line_number > 1:
        add_issue(
            file_path=file_path,
            line_number=line_number,
            issue_type="redundant",
            description="Unnecessary 'pass' statement",
            code=line.strip(),
            fix=""
        )
        issues_found += 1
    
    # Check for redundant parentheses in if statements
    if_pattern = r'if\s+\(\s*(.*?)\s*\)\s*:'
    for match in re.finditer(if_pattern, line):
        condition = match.group(1)
        
        # Skip if the condition contains tuple unpacking or complex expressions
        if ',' in condition or any(op in condition for op in ['and', 'or', 'not', '==', '!=', '<', '>', '<=', '>=']):
            continue
        
        add_issue(
            file_path=file_path,
            line_number=line_number,
            issue_type="redundant",
            description="Redundant parentheses in if statement",
            code=f"if ({condition}):",
            fix=f"if {condition}:"
        )
        issues_found += 1
    
    # Check for repeated string conversion
    str_pattern = r'str\(str\((.*?)\)\)'
    for match in re.finditer(str_pattern, line):
        expr = match.group(1)
        
        add_issue(
            file_path=file_path,
            line_number=line_number,
            issue_type="redundant",
            description="Redundant str() conversion",
            code=f"str(str({expr}))",
            fix=f"str({expr})"
        )
        issues_found += 1
    
    # Fix issues if requested
    if fix and issues_found > 0:
        for issue in CLEANUP_RESULTS["all_issues"][-issues_found:]:
            fix_issue(issue, dry_run=False)
    
    return issues_found

def check_imports(file_path, line_number, line, fix=False):
    """Check imports in a line
    
    Args:
        file_path: Path to the file
        line_number: Line number
        line: Line content
        fix: Whether to fix issues
        
    Returns:
        Number of issues found
    """
    issues_found = 0
    
    # Check for wildcard imports
    wildcard_pattern = r'from\s+([\w\.]+)\s+import\s+\*'
    match = re.match(wildcard_pattern, line)
    if match:
        module = match.group(1)
        
        add_issue(
            file_path=file_path,
            line_number=line_number,
            issue_type="import",
            description=f"Wildcard import from {module}",
            code=line.strip(),
            fix=None  # No automatic fix for wildcard imports
        )
        issues_found += 1
    
    # Check for unused imports (requires more context, simplified here)
    # This is a simplification; a proper implementation would need to analyze the whole file
    
    return issues_found

def check_dead_code(file_path, content, fix=False):
    """Check for dead code in a file
    
    Args:
        file_path: Path to the file
        content: File content
        fix: Whether to fix issues
        
    Returns:
        Number of issues found
    """
    issues_found = 0
    
    # Check for commented out code blocks
    comment_block_pattern = r'(#\s*.*\n){3,}'
    for match in re.finditer(comment_block_pattern, content):
        block = match.group(0)
        
        # Check if the block looks like code (has indentation, function calls, etc.)
        if re.search(r'#\s+(def|class|if|for|while|try|return)', block):
            line_number = content[:match.start()].count('\n') + 1
            
            add_issue(
                file_path=file_path,
                line_number=line_number,
                issue_type="dead",
                description="Commented out code block",
                code=block,
                fix=None  # No automatic fix for commented code
            )
            issues_found += 1
    
    # Check for unreachable code (simplified)
    # This is a simplification; a proper implementation would need more sophisticated analysis
    
    return issues_found

def scan_directory(directory, fix=False):
    """Scan a directory recursively for Python files
    
    Args:
        directory: Directory to scan
        fix: Whether to fix issues
        
    Returns:
        Total number of issues found
    """
    total_issues = 0
    
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and virtual environments
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', '__pycache__')]
        
        # Process Python files
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_issues += scan_python_file(file_path, fix)
    
    return total_issues

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Code cleanup script")
    parser.add_argument('--fix', action='store_true', help='Fix issues automatically')
    parser.add_argument('--dir', default='.', help='Directory to scan')
    
    args = parser.parse_args()
    
    logger.info(f"Starting code cleanup {'with fixes' if args.fix else 'in analysis mode'}")
    
    # Scan directory
    total_issues = scan_directory(args.dir, args.fix)
    
    # Print summary
    logger.info(f"Code cleanup completed")
    logger.info(f"Files scanned: {CLEANUP_RESULTS['files_scanned']}")
    logger.info(f"Files modified: {CLEANUP_RESULTS['files_modified']}")
    logger.info(f"Total issues: {total_issues}")
    logger.info(f"  - Naming issues: {CLEANUP_RESULTS['naming_issues']}")
    logger.info(f"  - Redundant code: {CLEANUP_RESULTS['redundant_code']}")
    logger.info(f"  - Dead code: {CLEANUP_RESULTS['dead_code']}")
    logger.info(f"  - Import issues: {CLEANUP_RESULTS['import_issues']}")
    
    if args.fix:
        logger.info(f"Issues fixed: {CLEANUP_RESULTS['issues_fixed']}")
    
    # Write report
    with open('code_cleanup_report.txt', 'w') as f:
        f.write(f"Code Cleanup Report\n")
        f.write(f"=================\n\n")
        f.write(f"Files scanned: {CLEANUP_RESULTS['files_scanned']}\n")
        f.write(f"Files modified: {CLEANUP_RESULTS['files_modified']}\n")
        f.write(f"Total issues: {total_issues}\n")
        f.write(f"  - Naming issues: {CLEANUP_RESULTS['naming_issues']}\n")
        f.write(f"  - Redundant code: {CLEANUP_RESULTS['redundant_code']}\n")
        f.write(f"  - Dead code: {CLEANUP_RESULTS['dead_code']}\n")
        f.write(f"  - Import issues: {CLEANUP_RESULTS['import_issues']}\n\n")
        
        if args.fix:
            f.write(f"Issues fixed: {CLEANUP_RESULTS['issues_fixed']}\n\n")
        
        f.write(f"Detailed Issues\n")
        f.write(f"==============\n\n")
        
        for issue in CLEANUP_RESULTS["all_issues"]:
            f.write(f"File: {issue['file']}\n")
            f.write(f"Line: {issue['line']}\n")
            f.write(f"Type: {issue['type']}\n")
            f.write(f"Description: {issue['description']}\n")
            
            if issue['code']:
                f.write(f"Code: {issue['code']}\n")
            
            if issue['fix']:
                f.write(f"Fix: {issue['fix']}\n")
            
            f.write("\n")
    
    logger.info(f"Report written to code_cleanup_report.txt")

if __name__ == "__main__":
    main()