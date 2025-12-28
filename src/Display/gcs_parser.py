import re
from datetime import datetime

class DataParser:
    def __init__(self):
        self.buffer = ""
        self.current_data = {}
        
    def parse_serial_data(self, data):
        """Parse data dari Arduino receiver"""
        self.buffer += data
        lines = self.buffer.split('\n')
        self.buffer = lines[-1]  # Simpan incomplete line
        
        parsed_data = {}
        
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
                
            # Parse berdasarkan pattern yang dikirim Arduino
            if line.startswith("=========="):
                if self.current_data:
                    parsed_data = self.current_data.copy()
                    self.current_data = {}
                continue
                
            elif "Altitude:" in line:
                try:
                    match = re.search(r"Altitude:\s*([\d.-]+)", line)
                    if match:
                        self.current_data['altitude'] = float(match.group(1))
                except ValueError:
                    pass
                    
            elif "Latitude:" in line:
                try:
                    match = re.search(r"Latitude:\s*([\d.-]+)", line)
                    if match:
                        self.current_data['latitude'] = int(match.group(1))
                except ValueError:
                    pass
                    
            elif "Longitude:" in line:
                try:
                    match = re.search(r"Longitude:\s*([\d.-]+)", line)
                    if match:
                        self.current_data['longitude'] = int(match.group(1))
                except ValueError:
                    pass
                    
            elif "Battery:" in line:
                try:
                    match = re.search(r"Battery:\s*([\d.-]+)V\s*\((\d+)%\)", line)
                    if match:
                        self.current_data['voltage'] = float(match.group(1))
                        self.current_data['remaining'] = int(match.group(2))
                except ValueError:
                    pass
                    
            elif "Status:" in line:
                try:
                    match = re.search(r"Status:\s*(.+)", line)
                    if match:
                        self.current_data['status'] = match.group(1).strip()
                except:
                    pass
                    
            elif "Avg RSSI:" in line:
                try:
                    match = re.search(r"Avg RSSI:\s*([\d.-]+)", line)
                    if match:
                        self.current_data['rssi'] = float(match.group(1))
                except ValueError:
                    pass
                    
            elif "Avg SNR:" in line:
                try:
                    match = re.search(r"Avg SNR:\s*([\d.-]+)", line)
                    if match:
                        self.current_data['snr'] = float(match.group(1))
                except ValueError:
                    pass
                    
            elif "Cycle Time:" in line:
                try:
                    match = re.search(r"Cycle Time:\s*(\d+)", line)
                    if match:
                        self.current_data['cycle_time'] = int(match.group(1))
                except ValueError:
                    pass
        
        return parsed_data if parsed_data else None

    def parse_raw_packet(self, data):
        """Alternative parser untuk raw packet data"""
        data = data.strip()
        
        # Debug: print raw data
        print(f"RAW: {data}")
        
        parsed = {}
        
        try:
            if data.startswith("AL") and len(data) > 2:
                parsed['altitude'] = float(data[2:])
            elif data.startswith("LT") and len(data) > 2:
                parsed['latitude'] = int(data[2:])
            elif data.startswith("LN") and len(data) > 2:
                parsed['longitude'] = int(data[2:])
            elif data.startswith("BV") and len(data) > 2:
                parts = data[2:].split(',')
                if len(parts) == 2:
                    parsed['voltage'] = float(parts[0])
                    parsed['remaining'] = int(parts[1])
            elif data.startswith("ST") and len(data) > 2:
                parsed['status'] = data[2:]
        except ValueError as e:
            print(f"Parse error: {e} for data: {data}")
            
        return parsed