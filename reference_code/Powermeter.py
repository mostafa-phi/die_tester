import pyvisa, time


class KeysightN7749C:
    """
    Class to control the Powermeter interface Keysight N7749C
    """
    
    def __init__(self):
        """Initialize connection to the powermeter"""
        self.rm = pyvisa.ResourceManager()
        self.address = "TCPIP0::100.65.7.205::inst0::INSTR" # replace with the actual address
        try:
            
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # timeout 5 seconds

            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")

            self.device.write("*RST") # Reset the instrument
            self.device.write("*CLS") # Clear any existing errors
            
            # Set auto gain for best dynamic
            self.device.write(":sens1:pow:gain:auto 1")
            self.device.write(":sens1:pow:gain:auto 2")

        except Exception as e:
            print(f"Error Connecting to Powermeter interface: {e}")
            raise
        
    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()
            
    def power(self, channel):
        response = self.device.query(":fetc" + str(channel) + ":pow?")
        return float(response)

    def power_unit(self, channel, *unit):
        # set the unit of powermeter reading
        if len(unit) == 1:
            match unit[0]:
                case 'dBm':
                    u = '0'
                case 'W':
                    u = '1';
            self.device.write(":sens" + str(channel) + ":pow:unit " + u)
        else:          
            response = self.device.query(":sens" + str(channel) + ":pow:unit?")
            if response == '0\n':
                return "dBm"    
            elif response == '1\n':
                return "W"
            
    def wavelength(self, channel, *w):
        # set the wavelength, unit is meter
        if len(w) == 1:
            self.device.write(":sens" + str(channel) + ":pow:wav " + str(w[0]))
        else:
            response = self.device.query(":sens" + str(channel) + ":pow:wav?")
            return float(response)
            
    def averaging_time(self, channel, *t):
        # set the averaging time, unit is second
        if len(t) == 1:
            self.device.write(":sens" + str(channel) + ":pow:atim " + str(t[0]))
        else:
            response = self.device.query(":sens" + str(channel) + ":pow:atim?")
            return float(response)

    def continuous_mode(self, channel):
        # Enable continuous measurement
        self.device.write(":init" + str(channel) + ":cont on")
        print("Continuous measurement started. Press Ctrl+C to stop.")
        # Read power measurements continuously
        while True:
            time.sleep(0.5);
            power = self.device.query(":read" + str(channel) + ":pow?")
            print(power.strip() + ' ' + self.power_unit(channel))


