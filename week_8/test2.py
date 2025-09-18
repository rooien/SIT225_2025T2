import os
import sys
import logging
from datetime import datetime
import asyncio
import traceback
import threading
import time
import csv

from arduino_iot_cloud import ArduinoCloudClient
import dash
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output
import plotly.graph_objects as go
# import plotly.io as pio  # Commented out to avoid kaleido dependency

DEVICE_ID = "6c8475fb-9c60-4eca-a447-0f9afe37b9ac"
SECRET_KEY = "IR3SFdMWGtZLIIACkrAFiXJik"

# === Data Buffers ===
data_buffer_new = []  # Buffer 1: Continuously receives NEW complete samples
data_buffer_plot = []  # Buffer 2: Stores ALL complete samples to be plotted (accumulated)
INITIAL_THRESHOLD = 10  # Show first graph when we have 10 complete samples
sample_counter = 0  # Counter to track total complete samples received
current_sample = {
    'x_value': None, 'x_timestamp': None,
    'y_value': None, 'y_timestamp': None,
    'z_value': None, 'z_timestamp': None
}  # Temp holder for incoming sample with individual timestamps
graph_initialized = False  # Flag to track if first graph has been shown

# Global flag to control the client thread
stop_event = threading.Event()
data_lock = threading.Lock()  # Thread safety for data buffers

def add_complete_sample_to_buffer():
    """
    Adds a complete sample (with X, Y, Z) to the new data buffer.
    Each value keeps its own timestamp.
    """
    global data_buffer_new, sample_counter, current_sample
    
    # Check if we have all three values
    if (current_sample['x_value'] is not None and 
        current_sample['y_value'] is not None and 
        current_sample['z_value'] is not None):
        
        sample_counter += 1
        complete_sample = {
            'x_value': current_sample['x_value'],
            'x_timestamp': current_sample['x_timestamp'],
            'y_value': current_sample['y_value'], 
            'y_timestamp': current_sample['y_timestamp'],
            'z_value': current_sample['z_value'],
            'z_timestamp': current_sample['z_timestamp'],
            'sample_id': sample_counter
        }
        
        data_buffer_new.append(complete_sample)
        print(f"Complete sample {sample_counter} added:")
        print(f"  X={complete_sample['x_value']:.3f} at {complete_sample['x_timestamp']}")
        print(f"  Y={complete_sample['y_value']:.3f} at {complete_sample['y_timestamp']}")
        print(f"  Z={complete_sample['z_value']:.3f} at {complete_sample['z_timestamp']}")
        print(f"New buffer now has {len(data_buffer_new)} complete samples")
        
        # Reset current sample
        current_sample = {
            'x_value': None, 'x_timestamp': None,
            'y_value': None, 'y_timestamp': None,
            'z_value': None, 'z_timestamp': None
        }
        
        return True
    return False

def on_x_changed(client, value):
    global current_sample
    with data_lock:
        current_sample['x_value'] = value
        current_sample['x_timestamp'] = datetime.now().isoformat()
        print(f"X received: {value} at {current_sample['x_timestamp']}")
        add_complete_sample_to_buffer()

def on_y_changed(client, value):
    global current_sample
    with data_lock:
        current_sample['y_value'] = value
        current_sample['y_timestamp'] = datetime.now().isoformat()
        print(f"Y received: {value} at {current_sample['y_timestamp']}")
        add_complete_sample_to_buffer()

def on_z_changed(client, value):
    global current_sample
    with data_lock:
        current_sample['z_value'] = value
        current_sample['z_timestamp'] = datetime.now().isoformat()
        print(f"Z received: {value} at {current_sample['z_timestamp']}")
        add_complete_sample_to_buffer()

def move_new_data_to_plot_buffer():
    """
    Moves ALL new COMPLETE samples from buffer 1 (new) to buffer 2 (plot).
    This accumulates all complete samples in the plot buffer.
    Returns True if data was moved, False otherwise.
    """
    global data_buffer_plot, data_buffer_new
    
    with data_lock:
        if len(data_buffer_new) > 0:
            # Move ALL new complete samples to the plot buffer (accumulate)
            samples_to_move = len(data_buffer_new)
            data_buffer_plot.extend(data_buffer_new)
            
            # Clear the new buffer (samples moved to plot buffer)
            data_buffer_new.clear()
            
            print(f"Moved {samples_to_move} NEW complete samples to plot buffer.")
            print(f"Plot buffer now has {len(data_buffer_plot)} total complete samples.")
            print(f"New buffer cleared (size: {len(data_buffer_new)}).")
            return True
    return False

def save_data_to_csv(data_list):
    """
    Saves the data points to a CSV file with timestamp.
    """
    if not os.path.exists("plots"):
        os.makedirs("plots")
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = f"plots/data_{timestamp}.csv"
    
    # Write data to CSV
    with open(csv_filename, 'w', newline='') as csvfile:
        if data_list:
            fieldnames = ['timestamp', 'sample_id', 'x', 'y', 'z']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for data_point in data_list:
                writer.writerow(data_point)
            print(f"Data saved to {csv_filename}")

def save_plot_as_png(figure):
    """
    PNG saving disabled to avoid kaleido dependency issues.
    """
    print("PNG saving skipped (kaleido not available)")

# === Dash Application ===
app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='Arduino IoT Cloud Live Data'),
    html.Div(id='status', children='Waiting for data...'),
    html.Button('Refresh Graph', id='refresh-btn', n_clicks=0, 
                style={
                    'margin': '10px', 
                    'padding': '10px 20px', 
                    'fontSize': '16px',
                    'backgroundColor': '#007bff',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer'
                }),
    dcc.Graph(id='live-graph'),
    dcc.Interval(
        id='interval-component',
        interval=2*1000,  # Check every 2 seconds for status updates
        n_intervals=0
    )
])

@app.callback([Output('live-graph', 'figure'), Output('status', 'children')],
              [Input('interval-component', 'n_intervals'),
               Input('refresh-btn', 'n_clicks')])
def update_graph_live(n_intervals, n_clicks):
    """
    Callback to update the live graph:
    1. Initial graph when we have 30 samples
    2. Refresh graph when refresh button is clicked (if new data available)
    """
    global data_buffer_plot, graph_initialized
    
    # Get current buffer sizes
    with data_lock:
        new_samples_count = len(data_buffer_new)
        plot_samples_count = len(data_buffer_plot)
    
    # Check what triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        trigger_id = 'interval-component'
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    should_update = False
    update_reason = ""
    
    if trigger_id == 'refresh-btn' and n_clicks > 0:
        # Manual refresh clicked
        if new_samples_count > 0:
            should_update = True
            update_reason = f"Manual refresh: Adding {new_samples_count} new complete samples"
        else:
            # No new data, just return current graph
            update_reason = "Manual refresh: No new complete samples to add"
    elif trigger_id == 'interval-component' and not graph_initialized:
        # Auto-show first graph when we have 10 complete samples
        if new_samples_count >= INITIAL_THRESHOLD:
            should_update = True
            update_reason = f"Initial graph: Showing first {new_samples_count} complete samples"
            graph_initialized = True
    
    if should_update and move_new_data_to_plot_buffer():
        # Save data to CSV
        save_data_to_csv(data_buffer_plot)
        
        # Create the graph with ALL accumulated complete samples
        # Extract timestamps and values for each axis
        x_timestamps = []
        x_values = []
        y_timestamps = []
        y_values = []
        z_timestamps = []
        z_values = []
        
        for sample in data_buffer_plot:
            # Parse timestamps and convert to datetime objects for plotting
            x_time = datetime.fromisoformat(sample['x_timestamp'])
            y_time = datetime.fromisoformat(sample['y_timestamp'])
            z_time = datetime.fromisoformat(sample['z_timestamp'])
            
            x_timestamps.append(x_time)
            x_values.append(sample['x_value'])
            
            y_timestamps.append(y_time)
            y_values.append(sample['y_value'])
            
            z_timestamps.append(z_time)
            z_values.append(sample['z_value'])
        
        # Create the plot with three separate lines, each plotted against their actual timestamps
        fig = go.Figure()
        
        # Add X values line (plotted at X timestamps)
        fig.add_trace(go.Scatter(
            x=x_timestamps, 
            y=x_values,
            mode='lines+markers',
            name='X Values',
            line=dict(color='red'),
            marker=dict(size=4)
        ))
        
        # Add Y values line (plotted at Y timestamps) 
        fig.add_trace(go.Scatter(
            x=y_timestamps, 
            y=y_values,
            mode='lines+markers',
            name='Y Values',
            line=dict(color='green'),
            marker=dict(size=4)
        ))
        
        # Add Z values line (plotted at Z timestamps)
        fig.add_trace(go.Scatter(
            x=z_timestamps, 
            y=z_values,
            mode='lines+markers',
            name='Z Values',
            line=dict(color='blue'),
            marker=dict(size=4)
        ))
        
        first_sample = data_buffer_plot[0]["sample_id"] if data_buffer_plot else 0
        last_sample = data_buffer_plot[-1]["sample_id"] if data_buffer_plot else 0
        
        fig.update_layout(
            title=f'Live Data Plot - {len(data_buffer_plot)} complete samples (Sample IDs: {first_sample} to {last_sample})',
            xaxis_title='Time',
            yaxis_title='Value',
            hovermode='x unified',
            showlegend=True,
            xaxis=dict(
                tickformat='%H:%M:%S',  # Show time format
                tickmode='linear'
            )
        )
        
        # Save the plot as PNG (disabled for now)
        save_plot_as_png(fig)
        
        status_message = f"{update_reason}. Total complete samples displayed: {len(data_buffer_plot)}"
        
        return fig, status_message
    
    # Return current status without updating graph
    if not graph_initialized:
        if new_samples_count >= INITIAL_THRESHOLD:
            status_message = f"Ready! {new_samples_count} complete samples collected. Graph will appear automatically."
        else:
            status_message = f"Collecting initial data... ({new_samples_count}/{INITIAL_THRESHOLD} complete samples needed for first graph)"
    else:
        if new_samples_count > 0:
            status_message = f"Graph displayed with {plot_samples_count} complete samples. {new_samples_count} new complete samples ready. Click 'Refresh Graph' to update."
        else:
            status_message = f"Graph displayed with {plot_samples_count} complete samples. No new data. Waiting for more complete samples..."
    
    # Return existing graph or empty graph
    if graph_initialized and plot_samples_count > 0:
        # Return the current graph (don't change it)
        with data_lock:
            current_plot_data = data_buffer_plot.copy()
        
        if current_plot_data:
            # Extract timestamps and values for each axis
            x_timestamps = []
            x_values = []
            y_timestamps = []
            y_values = []
            z_timestamps = []
            z_values = []
            
            for sample in current_plot_data:
                # Parse timestamps and convert to datetime objects for plotting
                x_time = datetime.fromisoformat(sample['x_timestamp'])
                y_time = datetime.fromisoformat(sample['y_timestamp'])
                z_time = datetime.fromisoformat(sample['z_timestamp'])
                
                x_timestamps.append(x_time)
                x_values.append(sample['x_value'])
                
                y_timestamps.append(y_time)
                y_values.append(sample['y_value'])
                
                z_timestamps.append(z_time)
                z_values.append(sample['z_value'])
            
            fig = go.Figure()
            
            # Add X values line
            fig.add_trace(go.Scatter(
                x=x_timestamps, 
                y=x_values,
                mode='lines+markers',
                name='X Values',
                line=dict(color='red'),
                marker=dict(size=4)
            ))
            
            # Add Y values line
            fig.add_trace(go.Scatter(
                x=y_timestamps, 
                y=y_values,
                mode='lines+markers',
                name='Y Values',
                line=dict(color='green'),
                marker=dict(size=4)
            ))
            
            # Add Z values line
            fig.add_trace(go.Scatter(
                x=z_timestamps, 
                y=z_values,
                mode='lines+markers',
                name='Z Values',
                line=dict(color='blue'),
                marker=dict(size=4)
            ))
            
            first_sample = current_plot_data[0]["sample_id"] if current_plot_data else 0
            last_sample = current_plot_data[-1]["sample_id"] if current_plot_data else 0
            
            fig.update_layout(
                title=f'Live Data Plot - {len(current_plot_data)} complete samples (Sample IDs: {first_sample} to {last_sample})',
                xaxis_title='Time',
                yaxis_title='Value',
                hovermode='x unified',
                showlegend=True,
                xaxis=dict(
                    tickformat='%H:%M:%S',  # Show time format
                    tickmode='linear'
                )
            )
            
            return fig, status_message
    
    # Return empty figure for initial state
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title='Waiting for 10 complete samples (X, Y, Z)...',
        xaxis_title='Time',
        yaxis_title='Value'
    )
    
    return empty_fig, status_message

# === Arduino Client Thread ===
def arduino_client_thread():
    """
    Runs the Arduino Cloud client in a separate thread.
    """
    try:
        client = ArduinoCloudClient(device_id=DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY)
        
        client.register("px", value=None, on_write=on_x_changed)
        client.register("py", value=None, on_write=on_y_changed)
        client.register("pz", value=None, on_write=on_z_changed)
        
        print("Starting Arduino Cloud client...")
        client.start()
        
    except Exception as e:
        print(f"Error in Arduino client: {e}")
        traceback.print_exc()

def main():
    """
    Main function to start the Arduino client and Dash app.
    """
    try:
        # Start the Arduino client in a separate thread
        client_thread = threading.Thread(target=arduino_client_thread, daemon=True)
        client_thread.start()
        
        print("Starting Dash application...")
        print("Open your browser and go to: http://127.0.0.1:8050")
        
        # Start the Dash server
        app.run(host='127.0.0.1', port=8050, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("Stopping application...")
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
    finally:
        stop_event.set()
        print("Application stopped.")

if __name__ == "__main__":
    main()