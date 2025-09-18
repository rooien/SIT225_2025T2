import os
import sys
import logging
from datetime import datetime, timedelta
import asyncio
import traceback
import threading
import time
import csv
import math
from collections import deque
from typing import Dict, List, Optional, Tuple, Any

from arduino_iot_cloud import ArduinoCloudClient
import dash
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output
import plotly.graph_objects as go

DEVICE_ID = "6c8475fb-9c60-4eca-a447-0f9afe37b9ac"
SECRET_KEY = "IR3SFdMWGtZLIIACkrAFiXJik"

# ========== ADVANCED CONTINUOUS DATA HANDLER ==========

class SmoothContinuousDataHandler:
    """
    Advanced handler for smooth continuous data visualization.
    
    Features:
    - Adaptive buffering with overflow protection
    - Built-in data smoothing and interpolation 
    - Real-time anomaly detection
    - Performance monitoring
    - Thread-safe operations
    """
    
    def __init__(self, buffer_size: int = 500, display_window: int = 100, 
                 smoothing_factor: float = 0.15, anomaly_threshold: float = 3.0):
        """
        Initialize the smooth data handler.
        
        Args:
            buffer_size: Maximum data points to keep in memory
            display_window: Number of recent points to display
            smoothing_factor: 0-1, higher = more smoothing
            anomaly_threshold: Standard deviations for anomaly detection
        """
        self.buffer_size = buffer_size
        self.display_window = display_window
        self.smoothing_factor = smoothing_factor
        self.anomaly_threshold = anomaly_threshold
        
        # Advanced data structures - using deque for efficient operations
        self.data_streams = {}
        self.smoothed_streams = {}
        self.performance_metrics = {
            'total_points': 0,
            'anomalies_detected': 0,
            'data_rates': deque(maxlen=50),
            'last_update_time': time.time()
        }
        
        # Thread safety
        self.data_lock = threading.RLock()
        
    def register_stream(self, stream_name: str):
        """Register a new data stream with advanced buffering."""
        with self.data_lock:
            if stream_name not in self.data_streams:
                self.data_streams[stream_name] = deque(maxlen=self.buffer_size)
                self.smoothed_streams[stream_name] = deque(maxlen=self.buffer_size)
                print(f"Registered advanced stream: {stream_name}")
    
    def add_data_point(self, stream_name: str, value: float, timestamp: datetime = None):
        """
        Add data point with advanced processing including smoothing and anomaly detection.
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        with self.data_lock:
            # Auto-register stream if needed
            if stream_name not in self.data_streams:
                self.register_stream(stream_name)
            
            # Anomaly detection using statistical analysis
            is_anomaly = self._detect_anomaly(stream_name, value)
            if is_anomaly:
                self.performance_metrics['anomalies_detected'] += 1
                print(f"Anomaly detected in {stream_name}: {value}")
            
            # Apply exponential smoothing for noise reduction
            smoothed_value = self._apply_smoothing(stream_name, value)
            
            # Store raw and smoothed data
            data_point = {
                'timestamp': timestamp,
                'raw_value': value,
                'smoothed_value': smoothed_value,
                'is_anomaly': is_anomaly,
                'quality_score': 0.5 if is_anomaly else 1.0
            }
            
            self.data_streams[stream_name].append(data_point)
            self.performance_metrics['total_points'] += 1
            
            # Update performance metrics
            self._update_performance_metrics()
    
    def _detect_anomaly(self, stream_name: str, value: float) -> bool:
        """Advanced anomaly detection using z-score analysis."""
        if len(self.data_streams[stream_name]) < 20:
            return False
            
        # Get recent values for statistical analysis
        recent_values = [point['raw_value'] for point in 
                        list(self.data_streams[stream_name])[-20:]]
        
        # Calculate mean and standard deviation
        mean_val = sum(recent_values) / len(recent_values)
        variance = sum((x - mean_val) ** 2 for x in recent_values) / len(recent_values)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        if std_dev == 0:
            return False
            
        # Z-score anomaly detection
        z_score = abs((value - mean_val) / std_dev)
        return z_score > self.anomaly_threshold
    
    def _apply_smoothing(self, stream_name: str, value: float) -> float:
        """Apply exponential smoothing for noise reduction."""
        if not self.data_streams[stream_name]:
            return value
            
        # Get last smoothed value
        last_point = self.data_streams[stream_name][-1]
        last_smoothed = last_point['smoothed_value']
        
        # Apply exponential moving average
        alpha = self.smoothing_factor
        smoothed_value = alpha * value + (1 - alpha) * last_smoothed
        
        return smoothed_value
    
    def _update_performance_metrics(self):
        """Update system performance tracking."""
        current_time = time.time()
        
        # Calculate data rate
        time_diff = current_time - self.performance_metrics['last_update_time']
        if time_diff > 0:
            rate = 1.0 / time_diff
            self.performance_metrics['data_rates'].append(rate)
        
        self.performance_metrics['last_update_time'] = current_time
    
    def get_display_data(self, stream_name: str) -> Tuple[List, List, List]:
        """
        Get processed data ready for smooth visualization.
        
        Returns:
            Tuple of (timestamps, raw_values, smoothed_values)
        """
        with self.data_lock:
            if stream_name not in self.data_streams:
                return [], [], []
            
            # Get recent data points for display
            recent_data = list(self.data_streams[stream_name])[-self.display_window:]
            
            if not recent_data:
                return [], [], []
            
            # Extract data for visualization
            timestamps = [point['timestamp'] for point in recent_data]
            raw_values = [point['raw_value'] for point in recent_data]
            smoothed_values = [point['smoothed_value'] for point in recent_data]
            
            # Apply cubic-like interpolation for ultra-smooth curves
            if len(smoothed_values) >= 4:
                interpolated_values = self._cubic_interpolation(smoothed_values)
                return timestamps, raw_values, interpolated_values
            
            return timestamps, raw_values, smoothed_values
    
    def _cubic_interpolation(self, values: List[float]) -> List[float]:
        """
        Custom cubic interpolation implementation for smooth curves.
        No external dependencies required.
        """
        if len(values) < 4:
            return values
            
        interpolated = []
        
        for i in range(len(values)):
            if i == 0 or i == len(values) - 1:
                # Keep endpoints unchanged
                interpolated.append(values[i])
            else:
                # Apply cubic smoothing using neighboring points
                if i >= 2 and i < len(values) - 2:
                    # Use 4-point cubic interpolation
                    p0, p1, p2, p3 = values[i-2], values[i-1], values[i], values[i+1]
                    # Catmull-Rom spline calculation
                    smoothed = 0.5 * (2*p1 + (-p0 + p2) + (2*p0 - 5*p1 + 4*p2 - p3))
                    interpolated.append(smoothed)
                else:
                    # Simple weighted average for edge cases
                    weights = [0.25, 0.5, 0.25]
                    start_idx = max(0, i-1)
                    end_idx = min(len(values), i+2)
                    
                    weighted_sum = 0
                    weight_sum = 0
                    
                    for j, val in enumerate(values[start_idx:end_idx]):
                        if j < len(weights):
                            weighted_sum += val * weights[j]
                            weight_sum += weights[j]
                    
                    if weight_sum > 0:
                        interpolated.append(weighted_sum / weight_sum)
                    else:
                        interpolated.append(values[i])
        
        return interpolated
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get system performance statistics."""
        with self.data_lock:
            avg_rate = (sum(self.performance_metrics['data_rates']) / 
                       len(self.performance_metrics['data_rates']) 
                       if self.performance_metrics['data_rates'] else 0)
            
            return {
                'total_points': self.performance_metrics['total_points'],
                'anomalies': self.performance_metrics['anomalies_detected'],
                'avg_data_rate': avg_rate,
                'buffer_usage': sum(len(stream) for stream in self.data_streams.values())
            }

# ========== ENHANCED DATA BUFFERS ==========
# Using the advanced handler instead of simple lists
data_handler = SmoothContinuousDataHandler(
    buffer_size=800,
    display_window=150,
    smoothing_factor=0.2,
    anomaly_threshold=2.5
)

# Initialize streams
data_handler.register_stream('x_axis')
data_handler.register_stream('y_axis')
data_handler.register_stream('z_axis')

INITIAL_THRESHOLD = 10  # Show first graph when we have 10 complete samples
sample_counter = 0
current_sample = {
    'x_value': None, 'x_timestamp': None,
    'y_value': None, 'y_timestamp': None,
    'z_value': None, 'z_timestamp': None
}
graph_initialized = False

# Global flag to control the client thread
stop_event = threading.Event()
data_lock = threading.RLock()

def add_complete_sample_to_handler():
    """
    Process complete sample (X, Y, Z) through the advanced data handler.
    """
    global sample_counter, current_sample
    
    # Check if we have all three values
    if (current_sample['x_value'] is not None and 
        current_sample['y_value'] is not None and 
        current_sample['z_value'] is not None):
        
        sample_counter += 1
        
        # Add each axis to the advanced handler
        data_handler.add_data_point('x_axis', current_sample['x_value'], current_sample['x_timestamp'])
        data_handler.add_data_point('y_axis', current_sample['y_value'], current_sample['y_timestamp'])
        data_handler.add_data_point('z_axis', current_sample['z_value'], current_sample['z_timestamp'])
        
        print(f"Complete sample {sample_counter} processed:")
        print(f"  X={current_sample['x_value']:.3f} at {current_sample['x_timestamp']}")
        print(f"  Y={current_sample['y_value']:.3f} at {current_sample['y_timestamp']}")
        print(f"  Z={current_sample['z_value']:.3f} at {current_sample['z_timestamp']}")
        
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
        current_sample['x_timestamp'] = datetime.now()
        print(f"X received: {value}")
        add_complete_sample_to_handler()

def on_y_changed(client, value):
    global current_sample
    with data_lock:
        current_sample['y_value'] = value
        current_sample['y_timestamp'] = datetime.now()
        print(f"Y received: {value}")
        add_complete_sample_to_handler()

def on_z_changed(client, value):
    global current_sample
    with data_lock:
        current_sample['z_value'] = value
        current_sample['z_timestamp'] = datetime.now()
        print(f"Z received: {value}")
        add_complete_sample_to_handler()

def save_advanced_data_to_csv():
    """Save current data with advanced metadata to CSV."""
    if not os.path.exists("plots"):
        os.makedirs("plots")
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = f"plots/advanced_data_{timestamp}.csv"
    
    # Collect data from all streams
    all_data = []
    with data_handler.data_lock:
        for stream_name in ['x_axis', 'y_axis', 'z_axis']:
            if stream_name in data_handler.data_streams:
                for point in data_handler.data_streams[stream_name]:
                    all_data.append({
                        'stream': stream_name,
                        'timestamp': point['timestamp'].isoformat(),
                        'raw_value': point['raw_value'],
                        'smoothed_value': point['smoothed_value'],
                        'is_anomaly': point['is_anomaly'],
                        'quality_score': point['quality_score']
                    })
    
    # Write to CSV
    if all_data:
        with open(csv_filename, 'w', newline='') as csvfile:
            fieldnames = ['stream', 'timestamp', 'raw_value', 'smoothed_value', 'is_anomaly', 'quality_score']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for data_point in all_data:
                writer.writerow(data_point)
        print(f"Advanced data saved to {csv_filename}")

# ========== ENHANCED DASH APPLICATION ==========
app = dash.Dash(__name__)

app.layout = html.Div([
    # Enhanced Header
    html.Div([
        html.H1("Advanced Smooth Accelerometer Visualizer", 
               style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '10px'}),
        html.P("Real-time data with advanced smoothing, anomaly detection & performance monitoring",
              style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '14px'})
    ]),
    
    # Enhanced Control Panel
    html.Div([
        html.Div([
            html.Button('Save Advanced Data', id='save-advanced-btn', n_clicks=0,
                      style={
                          'backgroundColor': '#3498db', 'color': 'white', 
                          'border': 'none', 'padding': '10px 20px', 
                          'marginRight': '10px', 'borderRadius': '5px',
                          'cursor': 'pointer'
                      }),
            html.Button('Reset Buffers', id='reset-advanced-btn', n_clicks=0,
                      style={
                          'backgroundColor': '#e74c3c', 'color': 'white',
                          'border': 'none', 'padding': '10px 20px',
                          'borderRadius': '5px', 'cursor': 'pointer'
                      }),
        ], style={'textAlign': 'center', 'marginBottom': '15px'}),
        
        # Performance Status Panel
        html.Div(id='advanced-status-panel', 
                style={'textAlign': 'center', 'marginBottom': '15px',
                      'padding': '10px', 'backgroundColor': '#f8f9fa',
                      'borderRadius': '5px', 'fontSize': '14px'})
    ]),
    
    # Main Advanced Graph
    dcc.Graph(id='advanced-live-graph', style={'height': '500px', 'marginBottom': '20px'}),
    
    # Performance Metrics Graph  
    dcc.Graph(id='performance-metrics-graph', style={'height': '250px'}),
    
    # High-frequency update interval for smooth visualization
    dcc.Interval(
        id='advanced-interval-component',
        interval=150,  # 6.7 Hz updates for ultra-smooth visualization
        n_intervals=0
    )
])

@app.callback([Output('advanced-live-graph', 'figure'),
               Output('performance-metrics-graph', 'figure'),
               Output('advanced-status-panel', 'children')],
              [Input('advanced-interval-component', 'n_intervals'),
               Input('save-advanced-btn', 'n_clicks'),
               Input('reset-advanced-btn', 'n_clicks')])
def update_advanced_graph(n_intervals, save_clicks, reset_clicks):
    """
    Advanced callback with smooth visualization and performance monitoring.
    """
    global graph_initialized
    
    # Handle button clicks
    ctx = callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'save-advanced-btn' and save_clicks > 0:
            save_advanced_data_to_csv()
        elif trigger_id == 'reset-advanced-btn' and reset_clicks > 0:
            # Reset the advanced handler
            with data_handler.data_lock:
                for stream_name in data_handler.data_streams:
                    data_handler.data_streams[stream_name].clear()
                    data_handler.smoothed_streams[stream_name].clear()
                data_handler.performance_metrics['anomalies_detected'] = 0
                data_handler.performance_metrics['total_points'] = 0
            print("Advanced buffers reset!")
    
    # Check if we should initialize the graph
    total_samples = sample_counter
    if not graph_initialized and total_samples >= INITIAL_THRESHOLD:
        graph_initialized = True
    
    # Create main advanced graph
    main_fig = create_advanced_main_graph()
    
    # Create performance metrics graph
    perf_fig = create_performance_metrics_graph()
    
    # Create advanced status panel
    status_panel = create_advanced_status_panel(total_samples)
    
    return main_fig, perf_fig, status_panel

def create_advanced_main_graph():
    """Create the main accelerometer graph with advanced smoothing."""
    fig = go.Figure()
    
    colors = {'x_axis': '#e74c3c', 'y_axis': '#2ecc71', 'z_axis': '#3498db'}
    names = {'x_axis': 'X-Axis (Smoothed)', 'y_axis': 'Y-Axis (Smoothed)', 'z_axis': 'Z-Axis (Smoothed)'}
    
    for stream_name in ['x_axis', 'y_axis', 'z_axis']:
        timestamps, raw_values, smoothed_values = data_handler.get_display_data(stream_name)
        
        if timestamps and smoothed_values:
            # Add smoothed line with enhanced styling
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=smoothed_values,
                mode='lines',
                name=names[stream_name],
                line=dict(color=colors[stream_name], width=2.5, shape='spline'),
                hovertemplate=f'{names[stream_name]}<br>Time: %{{x}}<br>Value: %{{y:.4f}}<extra></extra>'
            ))
            
            # Add raw data as faint background (optional)
            if len(raw_values) > 0:
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=raw_values,
                    mode='lines',
                    name=f'{stream_name.upper()} Raw',
                    line=dict(color=colors[stream_name], width=1, dash='dot'),
                    opacity=0.3,
                    showlegend=False,
                    hoverinfo='skip'
                ))
    
    fig.update_layout(
        title='Real-time Accelerometer Data (Advanced Smoothed & Interpolated)',
        xaxis_title='Time',
        yaxis_title='Acceleration (g)',
        hovermode='x unified',
        showlegend=True,
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='white',
        font=dict(family="Arial", size=11),
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.5)'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(200,200,200,0.5)'
        )
    )
    
    return fig

def create_performance_metrics_graph():
    """Create performance monitoring visualization."""
    fig = go.Figure()
    
    # Get performance stats
    stats = data_handler.get_performance_stats()
    
    # Create performance indicators
    metrics = ['Total Points', 'Anomalies', 'Data Rate (Hz)', 'Buffer Usage']
    values = [
        stats['total_points'],
        stats['anomalies'],
        round(stats['avg_data_rate'], 1),
        stats['buffer_usage']
    ]
    colors = ['#3498db', '#e74c3c', '#f39c12', '#9b59b6']
    
    fig.add_trace(go.Bar(
        x=metrics,
        y=values,
        marker_color=colors,
        text=values,
        textposition='auto',
        hovertemplate='%{x}<br>Value: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title='Advanced System Performance Metrics',
        yaxis_title='Count/Rate',
        showlegend=False,
        height=250,
        margin=dict(l=50, r=50, t=40, b=50),
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='white'
    )
    
    return fig

def create_advanced_status_panel(total_samples):
    """Create advanced status information panel."""
    stats = data_handler.get_performance_stats()
    
    if not graph_initialized:
        if total_samples >= INITIAL_THRESHOLD:
            status_message = f"🟢 Ready! {total_samples} complete samples collected. Graph will appear automatically."
        else:
            status_message = f"🟡 Collecting data... ({total_samples}/{INITIAL_THRESHOLD} complete samples needed)"
    else:
        status_message = f"🟢 Live monitoring active with {total_samples} complete samples"
    
    status_items = [
        html.Div([
            html.Span(status_message, style={'fontWeight': 'bold', 'color': '#2c3e50'})
        ], style={'marginBottom': '10px'}),
        
        html.Div([
            html.Span("📊 ", style={'fontSize': '16px'}),
            html.Span(f"Data Rate: {stats['avg_data_rate']:.1f} Hz", 
                     style={'margin': '0 15px', 'color': '#34495e'}),
            html.Span("⚠️ ", style={'fontSize': '16px'}),
            html.Span(f"Anomalies: {stats['anomalies']}", 
                     style={'margin': '0 15px', 'color': '#e74c3c' if stats['anomalies'] > 0 else '#27ae60'}),
            html.Span("💾 ", style={'fontSize': '16px'}),
            html.Span(f"Buffer: {stats['buffer_usage']} points", 
                     style={'margin': '0 15px', 'color': '#8e44ad'})
        ])
    ]
    
    return status_items

# ========== ARDUINO CLIENT THREAD ==========
def arduino_client_thread():
    """
    Runs the Arduino Cloud client in a separate thread.
    """
    try:
        client = ArduinoCloudClient(device_id=DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY)
        
        client.register("px", value=None, on_write=on_x_changed)
        client.register("py", value=None, on_write=on_y_changed)
        client.register("pz", value=None, on_write=on_z_changed)
        
        print("Starting Advanced Arduino Cloud client...")
        client.start()
        
    except Exception as e:
        print(f"Error in Arduino client: {e}")
        traceback.print_exc()

def main():
    """
    Enhanced main function with advanced continuous data processing.
    """
    try:
        print("=== Advanced Smooth Continuous Data Visualizer ===")
        print("Features:")
        print("- Adaptive buffering with overflow protection")
        print("- Real-time data smoothing and interpolation")
        print("- Statistical anomaly detection")
        print("- Performance monitoring and metrics")
        print("- Ultra-smooth visualization at 6.7 Hz")
        print()
        
        # Start the Arduino client in a separate thread
        client_thread = threading.Thread(target=arduino_client_thread, daemon=True)
        client_thread.start()
        
        print("Starting Advanced Dash application...")
        print("Open your browser and go to: http://127.0.0.1:8050")
        
        # Start the Dash server
        app.run(host='127.0.0.1', port=8050, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("Advanced application stopped.")
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
    finally:
        stop_event.set()
        print("Advanced application terminated.")

if __name__ == "__main__":
    main()