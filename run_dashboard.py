"""
Convenience entry point to launch the AI-built Web Dashboard.
Usage:
    python run_dashboard.py
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.server import app

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀  LAUNCHING SKYPULSE WEATHER DASHBOARD")
    print("=" * 60)
    print("✨  AI-Engineered Frontend is ready!")
    print("🌐  Open your browser at: http://localhost:5000")
    print("📌  Press Ctrl + C in this terminal to stop the server.")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
