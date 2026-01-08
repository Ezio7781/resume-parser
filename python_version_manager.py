#!/usr/bin/env python3
"""
Python Version Compatibility Checker and Manager
Ensures Python version compatibility for deployment
"""

import sys
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    
    # Check minimum version requirement
    min_version = (3, 8, 0)
    if version >= min_version:
        print("[OK] Python version is compatible (>= 3.8)")
        return True
    else:
        print(f"[ERROR] Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print(f"   Requires Python {min_version[0]}.{min_version[1]}.{min_version[2]} or higher")
        return False


def check_platform_compatibility():
    """Check platform compatibility"""
    system = platform.system()
    machine = platform.machine()
    print(f"Platform: {system} {machine}")
    
    # Check for common platforms
    compatible_platforms = ['Windows', 'Linux', 'Darwin']  # Darwin = macOS
    if system in compatible_platforms:
        print("[OK] Platform is compatible")
        return True
    else:
        print(f"[ERROR] Platform {system} may not be fully supported")
        return False


def check_dependencies():
    """Check if all dependencies can be installed"""
    print("Checking dependencies compatibility...")
    
    try:
        # Check core dependencies
        import pandas
        import flask
        import werkzeug
        import cryptography
        print("[OK] Core dependencies are available")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        return False


def create_compatibility_report():
    """Create compatibility report for deployment"""
    print("\n" + "="*50)
    print("COMPATIBILITY REPORT FOR DEPLOYMENT")
    print("="*50)
    
    version_ok = check_python_version()
    platform_ok = check_platform_compatibility()
    deps_ok = check_dependencies()
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    if version_ok and platform_ok and deps_ok:
        print("[SUCCESS] ENVIRONMENT IS READY FOR DEPLOYMENT")
        return True
    else:
        print("[ERROR] ENVIRONMENT NEEDS FIXES BEFORE DEPLOYMENT")
        
        if not version_ok:
            print("   - Upgrade Python to 3.8+")
        if not platform_ok:
            print("   - Use Windows, Linux, or macOS")
        if not deps_ok:
            print("   - Install missing dependencies")
        
        return False


def get_deployment_recommendations():
    """Get recommendations for different deployment platforms"""
    recommendations = {
        "heroku": {
            "python_version": "python-3.11.7",
            "buildpacks": ["heroku/python"],
            "notes": "Reliable free tier, supports background workers"
        },
        "railway": {
            "python_version": "3.11",
            "notes": "Easy deployment, generous free tier"
        },
        "render": {
            "python_version": "3.11",
            "notes": "Modern platform, good free tier"
        },
        "fly.io": {
            "python_version": "3.11",
            "notes": "高性能, good for API services"
        }
    }
    
    return recommendations


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--deployments":
        print("DEPLOYMENT RECOMMENDATIONS:")
        for platform, info in get_deployment_recommendations().items():
            print(f"\n{platform.upper()}:")
            for key, value in info.items():
                print(f"  {key}: {value}")
    else:
        create_compatibility_report()