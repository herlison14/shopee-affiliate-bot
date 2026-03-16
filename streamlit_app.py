"""
Entry point for Streamlit Community Cloud deployment.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dashboard.cloud_app import main

if __name__ == "__main__":
    main()
