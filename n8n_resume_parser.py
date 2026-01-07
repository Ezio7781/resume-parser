#!/usr/bin/env python3
"""
Simplified Resume Parser for n8n Automation
Direct command-line interface for the resume parsing logic
Usage: python n8n_resume_parser.py <file_path>
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from resume_parser import extract_text, parse_resume
except ImportError:
    print("ERROR: resume_parser.py not found")
    sys.exit(1)


def extract_resume_text(file_path: str) -> str:
    """Extract text content from resume file"""
    try:
        text = extract_text(file_path)
        if text and text.strip():
            print(f"EXTRACTED_TEXT:{text}")
            return text
        else:
            print("EXTRACTED_TEXT:")
            return ""
    except Exception as e:
        print(f"ERROR:Failed to extract text from {file_path}: {str(e)}")
        return ""


def parse_resume_content(file_path: str, text_content: str = None) -> dict:
    """Parse resume and return structured data"""
    try:
        if text_content:
            # Parse from provided text
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(text_content)
                temp_path = f.name
            
            result = parse_resume(temp_path)
            os.unlink(temp_path)
        else:
            # Parse from file directly
            result = parse_resume(file_path)
        
        # Add metadata
        filename = Path(file_path).name
        
        output = {
            **result,
            "filename": filename,
            "file_path": file_path,
            "parsed_at": __import__('datetime').datetime.now().isoformat(),
            "success": bool(result.get('full_name') or result.get('email'))
        }
        
        print(json.dumps(output, indent=2))
        return output
        
    except Exception as e:
        error_output = {
            "filename": Path(file_path).name,
            "file_path": file_path,
            "error": str(e),
            "success": False,
            "parsed_at": __import__('datetime').datetime.now().isoformat()
        }
        print(json.dumps(error_output, indent=2))
        return error_output


def main():
    parser = argparse.ArgumentParser(description='Resume Parser for n8n Automation')
    parser.add_argument('file_path', help='Path to resume file')
    parser.add_argument('--extract-text-only', action='store_true', 
                       help='Only extract text content without parsing')
    
    args = parser.parse_args()
    
    file_path = args.file_path
    
    # Validate file exists
    if not os.path.exists(file_path):
        print(json.dumps({
            "error": f"File not found: {file_path}",
            "success": False
        }))
        sys.exit(1)
    
    if args.extract_text_only:
        extract_resume_text(file_path)
    else:
        parse_resume_content(file_path)


if __name__ == "__main__":
    main()