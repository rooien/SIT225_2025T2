import os
import sys
import logging
from datetime import datetime
import asyncio

import traceback

from arduino_iot_cloud import ArduinoCloudClient

DEVICE_ID  = "6c8475fb-9c60-4eca-a447-0f9afe37b9ac"
SECRET_KEY = "IR3SFdMWGtZLIIACkrAFiXJik"

# === Data Buffers ===
data_buffer_new = []
data_buffer_plot = []
BUFFER_SIZE = 30  # Number of data points to plot at once
PLOT_SAMPLE_DURATION = 10  # in seconds, for saving plot (e.g., 10 seconds worth of data)
DATA_PER_SECOND = 3  # Assuming a data point is received every 1/3 second
SAMPLES_TO_SAVE = PLOT_SAMPLE_DURATION * DATA_PER_SECOND

def on_x_changed(client, value): 
     global data_buffer_new
     print("x", value)

def on_y_changed(client, value): 
    global data_buffer_new
    print("y", value)

def on_z_changed(client, value): 
    global data_buffer_new
    print("z", value)

def main():
    client = ArduinoCloudClient (device_id = DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY)

    client.register("px" , value = None , on_write = on_x_changed)
    client.register("py", value=None, on_write = on_y_changed)
    client.register("pz", value=None, on_write = on_z_changed)

    # start cloud client
    client.start()


if __name__ == "__main__":
    try:
        main()  # main function which runs in an internal infinite loop
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_type, file=print)



import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
# import pandas as pd
import plotly.io as pio


# # === CONFIG (your Manual/Python device creds) ===
# DEVICE_ID  = "6c8475fb-9c60-4eca-a447-0f9afe37b9ac"
# SECRET_KEY = "IR3SFdMWGtZLIIACkrAFiXJik"



# Global flag to control the client thread
stop_event = threading.Event()


def move_data_to_plot_buffer():
    """
    Moves a fixed number of samples from the new data buffer to the plotting buffer.
    This function is called by the Dash interval.
    """
    global data_buffer_plot, data_buffer_new
    if len(data_buffer_new) >= BUFFER_SIZE:
        data_buffer_plot.clear()
        data_buffer_plot.extend(data_buffer_new[:BUFFER_SIZE])
        del data_buffer_new[:BUFFER_SIZE]
        print(f"Moved {BUFFER_SIZE} samples to plot buffer. New buffer size: {len(data_buffer_new)}")
        return True
    return False

def save_plot_and_data(figure, dataframe):
    """
    Saves a Plotly figure as a PNG and the corresponding data as a CSV file with a timestamp.
    """
    if not os.path.exists("plots"):
        os.makedirs("plots")
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Save the plot as a PNG image
    plot_filename = f"plots/plot_{timestamp}.png"
    pio.write_image(figure, plot_filename)
    print(f"Plot saved to {plot_filename}")

    # Save the data as a CSV file
    csv_filename = f"plots/data_{timestamp}.csv"
    dataframe.to_csv(csv_filename, index=False)
    print(f"Data saved to {csv_filename}")

# === Dash Application ===
app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='Arduino IoT Cloud Live Data'),
    dcc.Graph(id='live-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1*1000,  # in milliseconds (updates every 1 second)
        n_intervals=0
    )
])

# # @app.callback(Output('live-graph', 'figure'),
# #               [Input('interval-component', 'n_intervals')])
# # def update_graph_live(n):
# #     """
# #     Callback to update the live graph every second.
# #     """
# #     if move_data_to_plot_buffer():
# #         # Only create a figure if we have new data to plot
# #         # Create a dataframe from the plotting buffer
# #         df = pd.DataFrame({
# #             'timestamp': [datetime.now()] * len(data_buffer_plot),  # Or use a real timestamp if available
# #             'value': data_buffer_plot
# #         })
        
# #         fig = go.Figure(
# #             data=[go.Scatter(x=df.index, y=df['value'], mode='lines+markers')],
# #             layout=go.Layout(
# #                 title='Live Data Plot (Last 30 samples)',
# #                 yaxis={'title': 'Value'},
# #                 xaxis={'title': 'Sample Index'},
# #                 # Adjust y-axis range based on your data
# #                 yaxis_range=[-10, 10]
# #             )
# #         )
        
# #         # Save the plot and data
# #         save_plot_and_data(fig, df)
        
# #         return fig
    
# #     # Return an empty figure if there's no new data to plot
# #     return go.Figure()


# # === Arduino Client Thread ===
# def arduino_client_thread():
#     client = ArduinoCloudClient (device_id = DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY)

#     client.register("px" , value = None , on_write = on_x_changed)
#     client.register("py", value=None, on_write = on_y_changed)
#     client.register("pz", value=None, on_write = on_z_changed)

#     # start cloud client
#     client.start()
#     while not stop_event.is_set():
#         time.sleep(1)
    
#     print("Stopping Arduino Cloud client thread...")
#     # Clean shutdown of the client is handled by the library in the client.start() loop
#     # when it receives a termination signal. Here we just break the waiting loop.



# def main():
#     """
#     Main function to start the Arduino client and Dash app.
#     """
#     try:
#         # Start the Arduino client in a separate thread to not block the Dash app
#         client_thread = threading.Thread(target=arduino_client_thread)
#         client_thread.start()
        
#         # Start the Dash server
#         app.run(host='127.0.0.1', port = '8050', debug=True, use_reloader=False)  # use_reloader=False is crucial when using threads
        
#     except KeyboardInterrupt:
#         print("Stopping application...")
#     finally:
#         # Set the stop event to gracefully shut down the client thread
#         stop_event.set()



