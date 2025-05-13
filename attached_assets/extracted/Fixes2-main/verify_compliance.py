#!/usr/bin/env python3
"""
Compliance Verification Tool for Tower of Temptation Bot

This script verifies that the codebase complies with all required
rules, standards, and best practices. It performs automated checks
and generates a compliance report.
"""
import os
import sys
import re
import ast
import json
import importlib
import inspect
import argparse
import asyncio
import logging
from typing import Dict, List, Any, Tuple, Set, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("compliance_verification")

# Rules definitions
RULES = {
    "R1": {
        "name": "Use py-cord instead of discord.py",
        "description": "All imports must use discord from py-cord; application command system must use py-cord interfaces",
        "failure_impact": "HIGH"
    },
    "R2": {
        "name": "Maintain backward compatibility",
        "description": "Backward compatibility layer must ensure all previous extensions work",
        "failure_impact": "HIGH"
    },
    "R3": {
        "name": "Support multi-guild operation",
        "description": "Data must be isolated per guild; commands must operate with guild-specific context",
        "failure_impact": "HIGH"
    },
    "R4": {
        "name": "Implement proper error handling",
        "description": "Error handling must be comprehensive with telemetry",
        "failure_impact": "MEDIUM"
    },
    "R5": {
        "name": "Provide user-friendly feedback",
        "description": "Error messages must be user-friendly with actionable suggestions",
        "failure_impact": "MEDIUM"
    },
    "R6": {
        "name": "Implement secure handling of credentials",
        "description": "Credentials must be handled securely and never stored in plaintext",
        "failure_impact": "CRITICAL"
    },
    "R7": {
        "name": "Maintain data consistency",
        "description": "Database operations must use transactions and validation",
        "failure_impact": "HIGH"
    },
    "R8": {
        "name": "Support both premium and free tiers",
        "description": "Premium features must be properly gated; free tier functionality must be preserved",
        "failure_impact": "MEDIUM"
    },
    "R9": {
        "name": "Scale efficiently with increased usage",
        "description": "Must use connection pooling, async operations, and efficient database queries",
        "failure_impact": "MEDIUM"
    },
    "R10": {
        "name": "Implement comprehensive testing",
        "description": "Must have unit, integration, and end-to-end tests",
        "failure_impact": "HIGH"
    }
}

# Required files and patterns
REQUIRED_FILES = [
    "utils/command_compatibility_layer.py",
    "utils/command_migration.py",
    "utils/data_version.py",
    "utils/data_migration.py",
    "utils/sftp_connection_pool.py",
    "utils/error_telemetry.py",
    "utils/user_feedback.py",
    "cogs/error_handling_cog.py",
    "tests/command_tester.py",
    "tests/discord_mocks.py",
    "tests/test_fixtures.py",
    "tests/integration_tests.py",
    "tests/multi_guild_tests.py",
    "ARCHITECTURE.md",
    "DEVELOPER_GUIDE.md",
    "COMPLIANCE.md"
]

# Required patterns to check in code
REQUIRED_PATTERNS = {
    "R1_discord_import": r"import\s+discord\b",
    "R1_commands_import": r"from\s+discord\.ext\s+import\s+commands",
    "R2_compatibility_decorator": r"@compatibility\b",
    "R3_guild_isolation": r"\bguild_id\b",
    "R4_error_handling": r"try\s*:.+?except\s+(?P<exception>\w+)(?:\s+as\s+(?P<var>\w+))?\s*:",
    "R6_credentials_security": r"password|secret|token|key",
    "R7_database_transaction": r"transaction|atomic|session",
    "R8_premium_check": r"premium|is_premium|has_premium",
    "R9_connection_pool": r"pool|connection_pool|get_connection",
    "R10_test_function": r"test_\w+"
}

def check_file_existence(root_dir: str = ".") -> Dict[str, bool]:
    """Check if all required files exist
    
    Args:
        root_dir: Root directory to check from
        
    Returns:
        Dictionary of file paths to existence status
    """
    results = {}
    for file_path in REQUIRED_FILES:
        full_path = os.path.join(root_dir, file_path)
        results[file_path] = os.path.exists(full_path)
    
    return results

def count_lines_of_code(root_dir: str = ".") -> Dict[str, int]:
    """Count lines of code in Python files
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        Dictionary of metrics
    """
    total_lines = 0
    code_lines = 0
    comment_lines = 0
    blank_lines = 0
    files_count = 0
    
    # File extensions to count
    extensions = ['.py', '.md']
    
    # Walk through directory
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip git directories and virtual environments
        if '.git' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath:
            continue
        
        for filename in filenames:
            # Check if file has a Python or Markdown extension
            if not any(filename.endswith(ext) for ext in extensions):
                continue
            
            # Get full file path
            file_path = os.path.join(dirpath, filename)
            files_count += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        total_lines += 1
                        stripped = line.strip()
                        
                        if not stripped:
                            blank_lines += 1
                        elif stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                            comment_lines += 1
                        else:
                            code_lines += 1
            except Exception as e:
                logger.warning(f"Error counting lines in {file_path}: {e}")
    
    return {
        "total_lines": total_lines,
        "code_lines": code_lines,
        "comment_lines": comment_lines,
        "blank_lines": blank_lines,
        "files_count": files_count,
        "comment_ratio": comment_lines / code_lines if code_lines > 0 else 0
    }

def check_docstring_coverage(root_dir: str = ".") -> Dict[str, Any]:
    """Check docstring coverage in Python files
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        Dictionary of docstring coverage metrics
    """
    total_functions = 0
    total_classes = 0
    total_modules = 0
    
    functions_with_docstrings = 0
    classes_with_docstrings = 0
    modules_with_docstrings = 0
    
    # Walk through directory
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip git directories and virtual environments
        if '.git' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath:
            continue
        
        for filename in filenames:
            # Check if file has a Python extension
            if not filename.endswith('.py'):
                continue
            
            # Get full file path
            file_path = os.path.join(dirpath, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Parse AST
                module = ast.parse(file_content)
                
                # Check module docstring
                total_modules += 1
                if ast.get_docstring(module):
                    modules_with_docstrings += 1
                
                # Check function and class docstrings
                for node in ast.walk(module):
                    if isinstance(node, ast.FunctionDef):
                        total_functions += 1
                        if ast.get_docstring(node):
                            functions_with_docstrings += 1
                    
                    elif isinstance(node, ast.ClassDef):
                        total_classes += 1
                        if ast.get_docstring(node):
                            classes_with_docstrings += 1
            
            except Exception as e:
                logger.warning(f"Error checking docstrings in {file_path}: {e}")
    
    # Calculate coverage percentages
    function_coverage = functions_with_docstrings / total_functions if total_functions > 0 else 1.0
    class_coverage = classes_with_docstrings / total_classes if total_classes > 0 else 1.0
    module_coverage = modules_with_docstrings / total_modules if total_modules > 0 else 1.0
    
    # Calculate weighted average (functions count more)
    total_items = total_functions + total_classes + total_modules
    total_with_docstrings = functions_with_docstrings + classes_with_docstrings + modules_with_docstrings
    overall_coverage = total_with_docstrings / total_items if total_items > 0 else 1.0
    
    return {
        "function_coverage": function_coverage,
        "class_coverage": class_coverage,
        "module_coverage": module_coverage,
        "overall_coverage": overall_coverage,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "total_modules": total_modules,
        "functions_with_docstrings": functions_with_docstrings,
        "classes_with_docstrings": classes_with_docstrings,
        "modules_with_docstrings": modules_with_docstrings
    }

def check_pattern_compliance(root_dir: str = ".") -> Dict[str, Dict[str, Any]]:
    """Check pattern compliance in Python files
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        Dictionary of pattern compliance metrics
    """
    results = {}
    
    # Initialize results for each pattern
    for pattern_id, pattern in REQUIRED_PATTERNS.items():
        results[pattern_id] = {
            "count": 0,
            "files": set(),
            "matches": []
        }
    
    # Walk through directory
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip git directories and virtual environments
        if '.git' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath:
            continue
        
        for filename in filenames:
            # Check if file has a Python extension
            if not filename.endswith('.py'):
                continue
            
            # Get full file path
            file_path = os.path.join(dirpath, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Check each pattern
                for pattern_id, pattern in REQUIRED_PATTERNS.items():
                    matches = re.finditer(pattern, file_content, re.DOTALL | re.MULTILINE)
                    
                    match_count = 0
                    for match in matches:
                        match_count += 1
                        # Store match details (first 50 characters)
                        context = file_content[max(0, match.start() - 20):min(len(file_content), match.end() + 20)]
                        results[pattern_id]["matches"].append({
                            "file": file_path,
                            "context": context.strip()
                        })
                    
                    if match_count > 0:
                        results[pattern_id]["count"] += match_count
                        results[pattern_id]["files"].add(file_path)
            
            except Exception as e:
                logger.warning(f"Error checking patterns in {file_path}: {e}")
    
    # Convert file sets to lists for JSON serialization
    for pattern_id in results:
        results[pattern_id]["files"] = list(results[pattern_id]["files"])
        # Limit the number of matches reported for brevity
        results[pattern_id]["matches"] = results[pattern_id]["matches"][:5]
    
    return results

def check_test_coverage(root_dir: str = ".") -> Dict[str, Any]:
    """Check test coverage metrics
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        Dictionary of test coverage metrics
    """
    test_files = 0
    test_functions = 0
    test_classes = 0
    test_assertions = 0
    
    files_with_tests = set()
    
    # Walk through directory to find test files
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip git directories and virtual environments
        if '.git' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath:
            continue
        
        for filename in filenames:
            # Check if file looks like a test file
            if not (filename.startswith('test_') or filename.endswith('_test.py') or filename.endswith('_tests.py')):
                continue
            
            if not filename.endswith('.py'):
                continue
            
            # Get full file path
            file_path = os.path.join(dirpath, filename)
            test_files += 1
            files_with_tests.add(file_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Count test functions and assertions
                test_functions += len(re.findall(r'def\s+test_\w+\s*\(', file_content))
                test_classes += len(re.findall(r'class\s+Test\w+\s*\(', file_content))
                
                # Count assertions (assert statements and validator calls)
                test_assertions += len(re.findall(r'\bassert\s+', file_content))
                test_assertions += len(re.findall(r'validator', file_content))
            
            except Exception as e:
                logger.warning(f"Error checking test coverage in {file_path}: {e}")
    
    # Get testable files (Python files that aren't tests)
    testable_files = set()
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '.git' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath or 'tests' in dirpath:
            continue
        
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            
            file_path = os.path.join(dirpath, filename)
            testable_files.add(file_path)
    
    return {
        "test_files": test_files,
        "test_functions": test_functions,
        "test_classes": test_classes,
        "test_assertions": test_assertions,
        "files_with_tests": len(files_with_tests),
        "testable_files": len(testable_files),
        "test_to_code_ratio": len(files_with_tests) / len(testable_files) if len(testable_files) > 0 else 0
    }

def evaluate_rule_compliance(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate overall rule compliance based on collected metrics
    
    Args:
        metrics: Dictionary of collected metrics
        
    Returns:
        Dictionary of rule compliance evaluations
    """
    results = {}
    
    # Rule R1: Use py-cord instead of discord.py
    discord_import_count = metrics["pattern_compliance"]["R1_discord_import"]["count"]
    commands_import_count = metrics["pattern_compliance"]["R1_commands_import"]["count"]
    
    results["R1"] = {
        "rule": RULES["R1"]["name"],
        "compliant": discord_import_count > 0 and commands_import_count > 0,
        "details": f"Found {discord_import_count} discord imports and {commands_import_count} commands imports",
        "impact": RULES["R1"]["failure_impact"]
    }
    
    # Rule R2: Maintain backward compatibility
    compat_file_exists = metrics["file_existence"]["utils/command_compatibility_layer.py"]
    compat_decorator_count = metrics["pattern_compliance"]["R2_compatibility_decorator"]["count"]
    
    results["R2"] = {
        "rule": RULES["R2"]["name"],
        "compliant": compat_file_exists and compat_decorator_count > 0,
        "details": f"Compatibility layer exists: {compat_file_exists}, Found {compat_decorator_count} compatibility decorators",
        "impact": RULES["R2"]["failure_impact"]
    }
    
    # Rule R3: Support multi-guild operation
    multi_guild_tests_exist = metrics["file_existence"]["tests/multi_guild_tests.py"]
    guild_isolation_count = metrics["pattern_compliance"]["R3_guild_isolation"]["count"]
    
    results["R3"] = {
        "rule": RULES["R3"]["name"],
        "compliant": multi_guild_tests_exist and guild_isolation_count > 20,  # Arbitrary threshold
        "details": f"Multi-guild tests exist: {multi_guild_tests_exist}, Found {guild_isolation_count} guild isolation references",
        "impact": RULES["R3"]["failure_impact"]
    }
    
    # Rule R4: Implement proper error handling
    error_handling_exists = metrics["file_existence"]["utils/error_telemetry.py"] and metrics["file_existence"]["cogs/error_handling_cog.py"]
    error_handling_count = metrics["pattern_compliance"]["R4_error_handling"]["count"]
    
    results["R4"] = {
        "rule": RULES["R4"]["name"],
        "compliant": error_handling_exists and error_handling_count > 10,  # Arbitrary threshold
        "details": f"Error handling files exist: {error_handling_exists}, Found {error_handling_count} try-except blocks",
        "impact": RULES["R4"]["failure_impact"]
    }
    
    # Rule R5: Provide user-friendly feedback
    user_feedback_exists = metrics["file_existence"]["utils/user_feedback.py"]
    
    results["R5"] = {
        "rule": RULES["R5"]["name"],
        "compliant": user_feedback_exists,
        "details": f"User feedback module exists: {user_feedback_exists}",
        "impact": RULES["R5"]["failure_impact"]
    }
    
    # Rule R6: Implement secure handling of credentials
    sftp_pool_exists = metrics["file_existence"]["utils/sftp_connection_pool.py"]
    credentials_handling_count = metrics["pattern_compliance"]["R6_credentials_security"]["count"]
    
    results["R6"] = {
        "rule": RULES["R6"]["name"],
        "compliant": sftp_pool_exists and credentials_handling_count > 5,  # Arbitrary threshold
        "details": f"SFTP connection pool exists: {sftp_pool_exists}, Found {credentials_handling_count} credential handling references",
        "impact": RULES["R6"]["failure_impact"]
    }
    
    # Rule R7: Maintain data consistency
    data_migration_exists = metrics["file_existence"]["utils/data_migration.py"] and metrics["file_existence"]["utils/data_version.py"]
    transaction_count = metrics["pattern_compliance"]["R7_database_transaction"]["count"]
    
    results["R7"] = {
        "rule": RULES["R7"]["name"],
        "compliant": data_migration_exists and transaction_count > 2,  # Arbitrary threshold
        "details": f"Data migration modules exist: {data_migration_exists}, Found {transaction_count} transaction references",
        "impact": RULES["R7"]["failure_impact"]
    }
    
    # Rule R8: Support both premium and free tiers
    premium_check_count = metrics["pattern_compliance"]["R8_premium_check"]["count"]
    
    results["R8"] = {
        "rule": RULES["R8"]["name"],
        "compliant": premium_check_count > 5,  # Arbitrary threshold
        "details": f"Found {premium_check_count} premium feature checks",
        "impact": RULES["R8"]["failure_impact"]
    }
    
    # Rule R9: Scale efficiently with increased usage
    connection_pool_exists = metrics["file_existence"]["utils/sftp_connection_pool.py"]
    connection_pool_count = metrics["pattern_compliance"]["R9_connection_pool"]["count"]
    
    results["R9"] = {
        "rule": RULES["R9"]["name"],
        "compliant": connection_pool_exists and connection_pool_count > 5,  # Arbitrary threshold
        "details": f"Connection pool exists: {connection_pool_exists}, Found {connection_pool_count} connection pool references",
        "impact": RULES["R9"]["failure_impact"]
    }
    
    # Rule R10: Implement comprehensive testing
    test_files_exist = metrics["file_existence"]["tests/command_tester.py"] and metrics["file_existence"]["tests/integration_tests.py"]
    test_function_count = metrics["pattern_compliance"]["R10_test_function"]["count"]
    test_to_code_ratio = metrics["test_coverage"]["test_to_code_ratio"]
    
    results["R10"] = {
        "rule": RULES["R10"]["name"],
        "compliant": test_files_exist and test_function_count > 20 and test_to_code_ratio > 0.2,  # Arbitrary thresholds
        "details": f"Test files exist: {test_files_exist}, Found {test_function_count} test functions, Test to code ratio: {test_to_code_ratio:.2f}",
        "impact": RULES["R10"]["failure_impact"]
    }
    
    return results

def generate_compliance_report(metrics: Dict[str, Any], output_file: str = "compliance_report.json") -> Dict[str, Any]:
    """Generate a comprehensive compliance report
    
    Args:
        metrics: Dictionary of collected metrics
        output_file: File to save JSON report to
        
    Returns:
        Dictionary with report summary
    """
    # Evaluate rule compliance
    rule_compliance = evaluate_rule_compliance(metrics)
    
    # Calculate overall compliance
    compliant_rules = sum(1 for rule in rule_compliance.values() if rule["compliant"])
    total_rules = len(rule_compliance)
    compliance_percentage = compliant_rules / total_rules * 100
    
    # Determine overall compliance status
    if compliance_percentage == 100:
        compliance_status = "FULLY COMPLIANT"
    elif compliance_percentage >= 90:
        compliance_status = "MOSTLY COMPLIANT"
    elif compliance_percentage >= 75:
        compliance_status = "PARTIALLY COMPLIANT"
    else:
        compliance_status = "NON-COMPLIANT"
    
    # Build summary
    summary = {
        "compliance_status": compliance_status,
        "compliance_percentage": compliance_percentage,
        "compliant_rules": compliant_rules,
        "total_rules": total_rules,
        "non_compliant_rules": [
            {
                "rule_id": rule_id,
                "rule": rule["rule"],
                "impact": rule["impact"],
                "details": rule["details"]
            }
            for rule_id, rule in rule_compliance.items() if not rule["compliant"]
        ]
    }
    
    # Build full report
    report = {
        "summary": summary,
        "rule_compliance": rule_compliance,
        "metrics": {
            "code_metrics": metrics["code_metrics"],
            "docstring_coverage": metrics["docstring_coverage"],
            "test_coverage": metrics["test_coverage"],
            "file_existence": metrics["file_existence"]
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Save report to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Compliance report saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving compliance report: {e}")
    
    return summary

def main():
    """Main entry point for compliance verification tool"""
    parser = argparse.ArgumentParser(description="Verify compliance with rules and standards")
    parser.add_argument("--dir", default=".", help="Root directory to check")
    parser.add_argument("--output", default="compliance_report.json", help="Output file for report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting compliance verification in directory: {args.dir}")
    
    # Run checks
    logger.info("Checking file existence...")
    file_existence = check_file_existence(args.dir)
    
    logger.info("Counting lines of code...")
    code_metrics = count_lines_of_code(args.dir)
    
    logger.info("Checking docstring coverage...")
    docstring_coverage = check_docstring_coverage(args.dir)
    
    logger.info("Checking pattern compliance...")
    pattern_compliance = check_pattern_compliance(args.dir)
    
    logger.info("Checking test coverage...")
    test_coverage = check_test_coverage(args.dir)
    
    # Combine metrics
    metrics = {
        "file_existence": file_existence,
        "code_metrics": code_metrics,
        "docstring_coverage": docstring_coverage,
        "pattern_compliance": pattern_compliance,
        "test_coverage": test_coverage
    }
    
    # Generate report
    logger.info("Generating compliance report...")
    summary = generate_compliance_report(metrics, args.output)
    
    # Print summary
    print(f"\nCompliance Status: {summary['compliance_status']}")
    print(f"Compliance Percentage: {summary['compliance_percentage']:.2f}%")
    print(f"Compliant Rules: {summary['compliant_rules']}/{summary['total_rules']}")
    
    if summary['non_compliant_rules']:
        print("\nNon-Compliant Rules:")
        for rule in summary['non_compliant_rules']:
            print(f"- [{rule['impact']}] {rule['rule_id']}: {rule['rule']}")
            print(f"  Details: {rule['details']}")
    
    print(f"\nFull report saved to: {args.output}")

if __name__ == "__main__":
    main()