# src/app.py
# import dash
# from components.layout import app_layout
# #from components.callbacks import * 
# import components.callbacks

# app = dash.Dash(__name__)
# app.layout = app_layout

# if __name__ == "__main__":
#     app.run_server(debug=True)


# src/app.py
from server import app  # Import app from server.py
import components.layout  # Ensures layout and callbacks are registered

if __name__ == "__main__":
    app.run_server(debug=True)

