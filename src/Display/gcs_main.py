import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
from datetime import datetime
import threading
import time
import json
import os
from gcs_parser import DataParser  # Import parser kita

# Set theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class UAVGCSApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("UAV Ground Control Station - LoRa MAVLink")
        self.geometry("1400x900")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Data storage
        self.data_log = []
        self.connected = False
        self.ser = None
        self.parser = DataParser()  # Initialize parser
        self.logging_active = False
        
        # Setup GUI
        self.setup_gui()
        
        # Auto-detect port
        self.auto_detect_port()
    
    def setup_gui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Status and Controls
        left_frame = ctk.CTkFrame(main_frame, width=350)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # Right panel - Charts and Map
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)
        
        self.setup_left_panel(left_frame)
        self.setup_right_panel(right_frame)
    
    def setup_left_panel(self, parent):
        # Title
        title_label = ctk.CTkLabel(parent, text="UAV GCS - LoRa", 
                                  font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)
        
        # Connection frame
        conn_frame = ctk.CTkFrame(parent)
        conn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(conn_frame, text="Connection Settings", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.port_var = ctk.StringVar(value="COM3")
        port_combo = ctk.CTkComboBox(conn_frame, values=self.get_serial_ports(),
                                   variable=self.port_var)
        port_combo.pack(fill="x", pady=5)
        
        self.connect_btn = ctk.CTkButton(conn_frame, text="Connect", 
                                       command=self.toggle_connection)
        self.connect_btn.pack(fill="x", pady=5)
        
        # Status indicators
        self.setup_status_indicators(parent)
        
        # Data display
        self.setup_data_display(parent)
        
        # Controls
        self.setup_controls(parent)
    
    def setup_status_indicators(self, parent):
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(status_frame, text="System Status", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Connection status
        self.conn_status = ctk.CTkLabel(status_frame, text="DISCONNECTED", 
                                       text_color="red", font=ctk.CTkFont(weight="bold"))
        self.conn_status.pack(pady=2)
        
        # Data reception status
        self.data_status = ctk.CTkLabel(status_frame, text="Last Data: Never", 
                                       text_color="yellow")
        self.data_status.pack(pady=2)
        
        # Packet count
        self.packet_count = 0
        self.packet_label = ctk.CTkLabel(status_frame, text="Packets: 0")
        self.packet_label.pack(pady=2)
    
    def setup_data_display(self, parent):
        data_frame = ctk.CTkFrame(parent)
        data_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(data_frame, text="Telemetry Data", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Real-time data labels dengan font lebih besar
        self.alt_label = ctk.CTkLabel(data_frame, text="Altitude: -- m", 
                                     font=ctk.CTkFont(size=14))
        self.alt_label.pack(pady=3)
        
        self.lat_label = ctk.CTkLabel(data_frame, text="Latitude: --", 
                                     font=ctk.CTkFont(size=14))
        self.lat_label.pack(pady=3)
        
        self.lon_label = ctk.CTkLabel(data_frame, text="Longitude: --", 
                                     font=ctk.CTkFont(size=14))
        self.lon_label.pack(pady=3)
        
        self.batt_label = ctk.CTkLabel(data_frame, text="Battery: -- V (--%)", 
                                      font=ctk.CTkFont(size=14))
        self.batt_label.pack(pady=3)
        
        self.status_label = ctk.CTkLabel(data_frame, text="Status: --", 
                                       font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=3)
        
        self.rssi_label = ctk.CTkLabel(data_frame, text="RSSI: -- dBm", 
                                      font=ctk.CTkFont(size=14))
        self.rssi_label.pack(pady=3)
        
        self.snr_label = ctk.CTkLabel(data_frame, text="SNR: -- dB", 
                                     font=ctk.CTkFont(size=14))
        self.snr_label.pack(pady=3)
        
        # Raw data display untuk debugging
        self.raw_label = ctk.CTkLabel(data_frame, text="Raw: --", 
                                     text_color="gray", font=ctk.CTkFont(size=10))
        self.raw_label.pack(pady=5)
    
    def setup_controls(self, parent):
        control_frame = ctk.CTkFrame(parent)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(control_frame, text="Data Controls", 
                    font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.log_btn = ctk.CTkButton(control_frame, text="Start Logging", 
                                   command=self.toggle_logging)
        self.log_btn.pack(fill="x", pady=5)
        
        export_btn = ctk.CTkButton(control_frame, text="Export to Excel", 
                                 command=self.export_data)
        export_btn.pack(fill="x", pady=5)
        
        clear_btn = ctk.CTkButton(control_frame, text="Clear Data", 
                                command=self.clear_data)
        clear_btn.pack(fill="x", pady=5)
        
        # Debug button
        debug_btn = ctk.CTkButton(control_frame, text="Debug Info", 
                                command=self.show_debug_info)
        debug_btn.pack(fill="x", pady=5)
    
    def setup_right_panel(self, parent):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Telemetry tab
        telemetry_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(telemetry_frame, text="Telemetry Charts")
        
        # Charts
        self.setup_charts(telemetry_frame)
        
        # Data tab
        data_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(data_frame, text="Data Log")
        self.setup_log_view(data_frame)
        
        # Raw Data tab
        raw_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(raw_frame, text="Raw Data")
        self.setup_raw_view(raw_frame)
    
    def setup_charts(self, parent):
        # Create figure for plots
        self.fig = Figure(figsize=(10, 8), dpi=100)
        
        # Subplots
        self.alt_ax = self.fig.add_subplot(311)
        self.batt_ax = self.fig.add_subplot(312)
        self.signal_ax = self.fig.add_subplot(313)
        
        # Setup plots
        self.setup_altitude_plot()
        self.setup_battery_plot()
        self.setup_signal_plot()
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def setup_altitude_plot(self):
        self.alt_ax.set_title('Altitude Trend', fontweight='bold')
        self.alt_ax.set_ylabel('Altitude (m)')
        self.alt_ax.grid(True, alpha=0.3)
        self.alt_line, = self.alt_ax.plot([], [], 'b-', linewidth=2)
        self.alt_data = []
        self.alt_times = []
    
    def setup_battery_plot(self):
        self.batt_ax.set_title('Battery Status', fontweight='bold')
        self.batt_ax.set_ylabel('Voltage (V)')
        self.batt_ax.grid(True, alpha=0.3)
        self.batt_line, = self.batt_ax.plot([], [], 'g-', linewidth=2)
        self.batt_data = []
        self.batt_times = []
    
    def setup_signal_plot(self):
        self.signal_ax.set_title('Signal Quality', fontweight='bold')
        self.signal_ax.set_ylabel('dB / dBm')
        self.signal_ax.grid(True, alpha=0.3)
        self.rssi_line, = self.signal_ax.plot([], [], 'r-', linewidth=2, label='RSSI')
        self.snr_line, = self.signal_ax.plot([], [], 'y-', linewidth=2, label='SNR')
        self.signal_ax.legend()
        self.rssi_data = []
        self.snr_data = []
        self.signal_times = []
    
    def setup_log_view(self, parent):
        # Create treeview for data log
        columns = ("Time", "Altitude", "Latitude", "Longitude", "Battery", "Status", "RSSI", "SNR")
        self.log_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.log_tree.heading(col, text=col)
            self.log_tree.column(col, width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_raw_view(self, parent):
        # Text widget untuk raw data
        self.raw_text = tk.Text(parent, wrap=tk.WORD, width=80, height=20, 
                               bg='black', fg='green', font=('Consolas', 10))
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.raw_text.yview)
        self.raw_text.configure(yscrollcommand=scrollbar.set)
        
        self.raw_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def auto_detect_port(self):
        ports = self.get_serial_ports()
        if ports:
            self.port_var.set(ports[0])
    
    def toggle_connection(self):
        if not self.connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        try:
            self.ser = serial.Serial(
                port=self.port_var.get(),
                baudrate=115200,
                timeout=1
            )
            self.connected = True
            self.connect_btn.configure(text="Disconnect")
            self.conn_status.configure(text="CONNECTED", text_color="green")
            
            # Start reading thread
            self.read_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.read_thread.start()
            
            messagebox.showinfo("Connected", f"Successfully connected to {self.port_var.get()}")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Cannot connect to {self.port_var.get()}\n{str(e)}")
    
    def disconnect_serial(self):
        self.connected = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connect_btn.configure(text="Connect")
        self.conn_status.configure(text="DISCONNECTED", text_color="red")
    
    def read_serial(self):
        while self.connected:
            try:
                if self.ser and self.ser.in_waiting:
                    raw_data = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if raw_data:
                        self.process_received_data(raw_data)
                time.sleep(0.01)
            except Exception as e:
                print(f"Read error: {e}")
                break
    
    def process_received_data(self, raw_data):
        # Update raw data display
        self.raw_label.configure(text=f"Raw: {raw_data[:50]}...")
        self.add_raw_data(f"{datetime.now().strftime('%H:%M:%S')} > {raw_data}\n")
        
        # Parse data
        parsed_data = self.parser.parse_serial_data(raw_data + '\n')
        
        if parsed_data:
            self.packet_count += 1
            self.packet_label.configure(text=f"Packets: {self.packet_count}")
            self.data_status.configure(text=f"Last Data: {datetime.now().strftime('%H:%M:%S')}", 
                                     text_color="green")
            
            # Update display dengan data yang berhasil di-parse
            self.update_display(parsed_data)
    
    def update_display(self, data):
        # Update labels
        if 'altitude' in data:
            self.alt_label.configure(text=f"Altitude: {data['altitude']:.2f} m")
        if 'latitude' in data:
            self.lat_label.configure(text=f"Latitude: {data['latitude']}")
        if 'longitude' in data:
            self.lon_label.configure(text=f"Longitude: {data['longitude']}")
        if 'voltage' in data and 'remaining' in data:
            batt_color = "green" if data['remaining'] > 20 else "red"
            self.batt_label.configure(text=f"Battery: {data['voltage']:.2f} V ({data['remaining']}%)",
                                    text_color=batt_color)
        if 'status' in data:
            status_color = "green" if data['status'] == "OK" else "red"
            self.status_label.configure(text=f"Status: {data['status']}", 
                                      text_color=status_color)
        if 'rssi' in data:
            rssi_color = "green" if data['rssi'] > -90 else "red"
            self.rssi_label.configure(text=f"RSSI: {data['rssi']:.2f} dBm", 
                                    text_color=rssi_color)
        if 'snr' in data:
            self.snr_label.configure(text=f"SNR: {data['snr']:.2f} dB")
        
        # Update charts
        self.update_charts(data)
        
        # Log data
        if self.logging_active:
            self.log_data(data)
    
    def update_charts(self, data):
        current_time = datetime.now()
        
        # Update altitude chart
        if 'altitude' in data:
            self.alt_data.append(data['altitude'])
            self.alt_times.append(current_time)
            if len(self.alt_data) > 50:
                self.alt_data.pop(0)
                self.alt_times.pop(0)
            
            self.alt_line.set_data(range(len(self.alt_data)), self.alt_data)
            self.alt_ax.relim()
            self.alt_ax.autoscale_view()
        
        # Update battery chart
        if 'voltage' in data:
            self.batt_data.append(data['voltage'])
            self.batt_times.append(current_time)
            if len(self.batt_data) > 50:
                self.batt_data.pop(0)
                self.batt_times.pop(0)
            
            self.batt_line.set_data(range(len(self.batt_data)), self.batt_data)
            self.batt_ax.relim()
            self.batt_ax.autoscale_view()
        
        # Update signal chart
        if 'rssi' in data:
            self.rssi_data.append(data['rssi'])
            self.signal_times.append(current_time)
            if len(self.rssi_data) > 50:
                self.rssi_data.pop(0)
                self.signal_times.pop(0)
            
            self.rssi_line.set_data(range(len(self.rssi_data)), self.rssi_data)
            
        if 'snr' in data:
            self.snr_data.append(data['snr'])
            if len(self.snr_data) > 50:
                self.snr_data.pop(0)
            
            self.snr_line.set_data(range(len(self.snr_data)), self.snr_data)
            self.signal_ax.relim()
            self.signal_ax.autoscale_view()
        
        self.canvas.draw_idle()
    
    def toggle_logging(self):
        self.logging_active = not self.logging_active
        if self.logging_active:
            self.log_btn.configure(text="Stop Logging", fg_color="red")
            messagebox.showinfo("Logging", "Data logging started!")
        else:
            self.log_btn.configure(text="Start Logging", fg_color="#1f6aa5")
            messagebox.showinfo("Logging", f"Data logging stopped! Total records: {len(self.data_log)}")
    
    def log_data(self, data):
        log_entry = {
            'timestamp': datetime.now(),
            'altitude': data.get('altitude', 0),
            'latitude': data.get('latitude', 0),
            'longitude': data.get('longitude', 0),
            'voltage': data.get('voltage', 0),
            'remaining': data.get('remaining', 0),
            'status': data.get('status', ''),
            'rssi': data.get('rssi', 0),
            'snr': data.get('snr', 0)
        }
        
        self.data_log.append(log_entry)
        
        # Update log view
        self.update_log_view(log_entry)
    
    def update_log_view(self, data):
        self.log_tree.insert("", "end", values=(
            data['timestamp'].strftime("%H:%M:%S"),
            f"{data['altitude']:.2f}",
            data['latitude'],
            data['longitude'],
            f"{data['voltage']:.2f}",
            data['status'],
            f"{data['rssi']:.2f}",
            f"{data['snr']:.2f}"
        ))
        
        # Auto-scroll to bottom
        self.log_tree.see(self.log_tree.get_children()[-1])
    
    def add_raw_data(self, text):
        self.raw_text.insert('end', text)
        self.raw_text.see('end')
        # Keep only last 1000 lines
        lines = self.raw_text.get('1.0', 'end').split('\n')
        if len(lines) > 1000:
            self.raw_text.delete('1.0', f'{len(lines)-1000}.0')
    
    def export_data(self):
        if not self.data_log:
            messagebox.showwarning("No Data", "No data to export!")
            return
            
        try:
            filename = f"uav_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df = pd.DataFrame(self.data_log)
            df.to_excel(filename, index=False)
            messagebox.showinfo("Export Successful", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def clear_data(self):
        self.data_log.clear()
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        self.raw_text.delete('1.0', 'end')
        self.packet_count = 0
        self.packet_label.configure(text="Packets: 0")
        messagebox.showinfo("Clear", "All data cleared!")
    
    def show_debug_info(self):
        info = f"Connected: {self.connected}\n"
        info += f"Packets Received: {self.packet_count}\n"
        info += f"Data Log Entries: {len(self.data_log)}\n"
        info += f"Logging Active: {self.logging_active}\n"
        info += f"Serial Port: {self.port_var.get()}"
        
        messagebox.showinfo("Debug Info", info)
    
    def on_closing(self):
        self.disconnect_serial()
        self.destroy()

if __name__ == "__main__":
    app = UAVGCSApp()
    app.mainloop()