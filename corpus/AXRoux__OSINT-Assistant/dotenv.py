"""
Python-dotenv

Loads environment variables from .env file

Usage:
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env in current directory
    load_dotenv('/path/to/.env')  # Load from specified file

This is a simplified standalone version of python-dotenv that can be placed
directly in your project folder if you're unable to install the package.
"""

import os
import io
import re
import sys
from typing import Dict, Optional, Union, Any, List, Iterator, TextIO


def load_dotenv(dotenv_path: Union[str, os.PathLike, None] = None, 
               override: bool = False, 
               encoding: Optional[str] = None) -> bool:
    """
    Load the environment variables from a .env file.
    
    Args:
        dotenv_path: Path to the .env file. If not provided, looks for .env in current directory
        override: Whether to override existing environment variables
        encoding: Encoding of the .env file
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    if dotenv_path is None:
        dotenv_path = os.path.join(os.getcwd(), '.env')
    
    if not os.path.exists(dotenv_path):
        return False
    
    try:
        with io.open(dotenv_path, encoding=encoding or 'utf-8') as f:
            env_vars = parse_dotenv(f)
    except Exception:
        return False
    
    for key, value in env_vars.items():
        if key in os.environ and not override:
            continue
        os.environ[key] = value
    
    return True


def dotenv_values(dotenv_path: Union[str, os.PathLike, None] = None, 
                 encoding: Optional[str] = None) -> Dict[str, str]:
    """
    Parse a .env file and return a dictionary of key-value pairs.
    This is the function that Flask CLI uses.
    
    Args:
        dotenv_path: Path to the .env file. If not provided, looks for .env in current directory
        encoding: Encoding of the .env file
        
    Returns:
        Dictionary of key-value pairs from the .env file
    """
    if dotenv_path is None:
        dotenv_path = os.path.join(os.getcwd(), '.env')
    
    if not os.path.exists(dotenv_path):
        return {}
    
    try:
        with io.open(dotenv_path, encoding=encoding or 'utf-8') as f:
            return parse_dotenv(f)
    except Exception:
        return {}


def parse_dotenv(file_obj: TextIO) -> Dict[str, str]:
    """Parse the contents of a .env file and return a dictionary of key-value pairs."""
    result = {}
    
    for line in file_obj:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Handle basic KEY=VALUE format
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if value and (
                (value[0] == value[-1] == '"') or 
                (value[0] == value[-1] == "'")
            ):
                value = value[1:-1]
            
            result[key] = value
    
    return result


def find_dotenv(filename: str = '.env', 
               raise_error_if_not_found: bool = False, 
               usecwd: bool = False) -> str:
    """
    Search for a .env file in parent directories.
    
    Args:
        filename: Name of the file to search for
        raise_error_if_not_found: Whether to raise an error if file is not found
        usecwd: Whether to use the current working directory
    
    Returns:
        Path to the found file
    
    Raises:
        IOError: If file is not found and raise_error_if_not_found is True
    """
    if usecwd:
        path = os.getcwd()
    else:
        frame = sys._getframe()
        current_file = __file__
        
        while frame.f_code.co_filename == current_file:
            frame = frame.f_back
        frame_filename = frame.f_code.co_filename
        path = os.path.dirname(os.path.abspath(frame_filename))
    
    for _ in range(10):  # Limit the number of parent directories to search
        check_path = os.path.join(path, filename)
        if os.path.exists(check_path):
            return check_path
        
        parent_path = os.path.dirname(path)
        if parent_path == path:
            break
        path = parent_path
    
    if raise_error_if_not_found:
        raise IOError(f"File {filename} not found")
    return ""


if __name__ == "__main__":
    print("This is a standalone version of python-dotenv.")
    print("To use it, import the module and call load_dotenv().")
    print("For example: from dotenv import load_dotenv; load_dotenv()") 