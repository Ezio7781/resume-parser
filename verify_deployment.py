#!/usr/bin/env python3
"""
Deployment Verification Checklist
Run this before deploying to ensure everything is ready
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename):
    """Check if a file exists"""
    exists = os.path.exists(filename)
    status = "✅" if exists else "❌"
    print(f"{status} {filename}")
    return exists

def check_content(filename, expected_strings):
    """Check if file contains expected strings"""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for expected in expected_strings:
                if expected in content:
                    print(f"  ✅ Contains: {expected}")
                else:
                    print(f"  ❌ Missing: {expected}")
                    return False
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Resume Parser - Deployment Verification Checklist")
    print("=" * 60)
    
    all_good = True
    
    print("\n📄 SOURCE FILES:")
    source_files = ['app.py', 'llm_helper.py', 'resume_parser.py', 'secrets_store.py']
    for f in source_files:
        all_good &= check_file_exists(f)
    
    print("\n📦 DEPLOYMENT FILES:")
    deployment_files = ['Procfile', 'runtime.txt', 'requirements.txt']
    for f in deployment_files:
        all_good &= check_file_exists(f)
    
    print("\n☁️  CLOUD PLATFORM CONFIGS:")
    cloud_files = {
        'railway.json': ['type'],
        'render.yaml': ['services'],
        '.replit': ['run'],
        'replit.nix': ['mkShell']
    }
    for f, expected in cloud_files.items():
        if check_file_exists(f):
            all_good &= check_content(f, expected)
    
    print("\n📚 DOCUMENTATION:")
    docs = {
        'README.md': ['Resume', 'Parser'],
        'README_PRODUCTION.md': ['production'],
        'DEPLOY_FREE.md': ['Render', 'Railway'],
        'DEPLOYMENT.md': ['Nginx', 'Supervisor'],
        'PRODUCTION_READY.md': ['Checklist'],
        'QUICK_REFERENCE.md': ['Quick'],
        'SECURITY_REPORT.md': ['Security']
    }
    for f, expected in docs.items():
        if check_file_exists(f):
            all_good &= check_content(f, expected)
    
    print("\n⚙️  CONFIGURATION:")
    config_files = {
        '.gitignore': ['__pycache__'],
        '.env.production': ['FLASK_ENV'],
        '.slugignore': ['__pycache__'],
        'requirements.txt': ['flask', 'gunicorn']
    }
    for f, expected in config_files.items():
        if check_file_exists(f):
            all_good &= check_content(f, expected)
    
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL CHECKS PASSED - READY TO DEPLOY!")
        print("\nNext steps:")
        print("1. git push to GitHub")
        print("2. Deploy to Render.com (see DEPLOY_FREE.md)")
        print("3. Set environment variables on platform dashboard")
        print("4. Test production URL")
        return 0
    else:
        print("❌ Some checks failed - see above")
        print("Missing files or configuration issues found")
        return 1

if __name__ == '__main__':
    sys.exit(main())
