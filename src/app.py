# src/app.py
from server import app  # Import app from server.py
import components.layout  # Ensures layout and callbacks are registered

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
