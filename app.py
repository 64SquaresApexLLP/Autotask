"""
TeamLogic-AutoTask Application
Core application without UI components.
"""

import warnings
warnings.filterwarnings("ignore", message="You have an incompatible version of 'pyarrow' installed")

import sys
import os

# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


def main():
    """Main application entry point."""
    print("TeamLogic-AutoTask Application")
    print("UI components have been removed.")
    print("This is now a core application without user interface.")


if __name__ == "__main__":
    main()
