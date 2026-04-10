import pyvisa

### Device class files
class Keysight8169A:
    """
    Class to control the Keysight/Agilent 8169A Polarization Controller via GPIB
    """
    def __init__(self, gpib_address=24):
        """Initialize connection to the polarization controller"""
        self.rm = pyvisa.ResourceManager()
        self.address = f"GPIB0::{gpib_address}::INSTR"
        try:
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # 5 seconds timeout
            self.device.write("*CLS")  # Clear status registers
            self.device.write("*RST")  # Reset to defaults
            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")
        except Exception as e:
            print(f"Error connecting to polarization controller: {e}")
            raise

    def set_poincare_coordinates(self, epsilon_b, theta_p):
        """
        Set the state of polarization using Poincaré sphere coordinates
        epsilon_b (float): 2εB coordinate (-720 to 720 degrees)
        theta_p (float): 2θP coordinate (-2160 to 2160 degrees)
        """
        # Ensure values are within range
        epsilon_b = max(min(epsilon_b, 720), -720)
        theta_p = max(min(theta_p, 2160), -2160)
        
        # Set coordinates
        self.device.write(f":INPut:CIRCle:EPSilonb {epsilon_b}")
        self.device.write(f":INPut:CIRCle:THETap {theta_p}")
        
        # Verify the settings (optional)
        set_epsilon = float(self.device.query(":INPut:CIRCle:EPSilonb?"))
        set_theta = float(self.device.query(":INPut:CIRCle:THETap?"))
        
        return set_epsilon, set_theta

    def set_wave_plates(self, quarter_pos, half_pos):
        """
        Set the position of the λ/4 and λ/2 retarder plates
        quarter_pos (float): Position of λ/4 plate (-360 to 360 degrees)
        half_pos (float): Position of λ/2 plate (-360 to 360 degrees)
        """
        # Ensure values are within range
        quarter_pos = max(min(quarter_pos, 360), -360)
        half_pos = max(min(half_pos, 360), -360)
        
        # Set positions
        self.device.write(f":INPut:POSition:QUARter {quarter_pos}")
        self.device.write(f":INPut:POSition:HALF {half_pos}")
        
        # Verify the settings (optional)
        set_quarter = float(self.device.query(":INPut:POSition:QUARter?"))
        set_half = float(self.device.query(":INPut:POSition:HALF?"))
        
        return set_quarter, set_half

    def set_polarizer_angle(self, position):
        """
        Set the position of the polarizing filter
        position (float): Angle in degrees (-360 to 360)
        """
        # Ensure value is within range
        position = max(min(position, 360), -360)
        
        # Set position
        self.device.write(f":INPut:POSition:POLarizer {position}")
        
        # Verify the setting (optional)
        set_position = float(self.device.query(":INPut:POSition:POLarizer?"))
        
        return set_position

    def scan_sphere(self, speed="FAST"):
        """
        Start scanning the Poincaré sphere 
        speed (str): "FAST" or "SLOW"
        """
        if speed.upper() not in ["FAST", "SLOW"]:
            raise ValueError("Speed must be 'FAST' or 'SLOW'")
            
        # Set speed (0 for SLOW, 1 for FAST)
        speed_val = 1 if speed.upper() == "FAST" else 0
        self.device.write(f":INPut:PSPHere:RATE {speed_val}")
        
        # Start the scan
        self.device.write(":INITiate:IMMediate")
        
    def stop_scan(self):
        """Stop the Poincaré sphere scan"""
        self.device.write(":ABORt")

    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()



class PAX1000Polarimeter:
    """
    Class to control the PAX1000 Polarimeter via VISA
    """
    def __init__(self, address='USB0::0x1313::0x8031::M01066988::INSTR'):
        """Initialize connection to the polarimeter"""
        self.rm = pyvisa.ResourceManager()
        self.address = address
        try:
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # 5 seconds timeout
            self.device.write("*CLS")   # Clear status registers
            self.device.write("*RST")   # Reset device

            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")

            # Ensure measurement mode is set to H1024
            self.device.write(":SENSe1:CALCulate:MODe 2")  # 2 = H1024
            mode = self.device.query(":SENSe1:CALCulate:MODe?").strip()
            if mode != "2":
                print(f"Warning: Measurement mode not set correctly! Current mode: {mode}")

            # Ensure the waveplate is rotating
            self.device.write(":INPut:ROTation:STATe ON")
            
        except Exception as e:
            print(f"Error connecting to polarimeter: {e}")
            raise

    def set_wavelength(self, wavelength):
        """ Set the operating wavelength in meters. """
        self.device.write(f":SENSe1:CORRection:WAVelength {wavelength}")
        return float(self.device.query(":SENSe1:CORRection:WAVelength?"))

    def set_auto_range(self, auto_mode=True):
        """ Enable or disable auto-ranging. """
        mode = 1 if auto_mode else 0
        self.device.write(f":SENSe1:POWer:RANGe:AUTO {mode}")
        return bool(int(self.device.query(":SENSe1:POWer:RANGe:AUTO?")))

    def set_power_range(self, index):
        """ Set the power range (1-16). """
        index = max(1, min(16, int(index)))
        self.device.write(f":SENSe1:POWer:RANGe:INDex {index}")
        return int(self.device.query(":SENSe1:POWer:RANGe:INDex?"))

    def read_polarization_data(self):
        """
        Read fresh polarization state data from the polarimeter.
        Ensures a valid fresh measurement is returned.
        """
        # Check for errors
        error = self.device.query(":SYSTem:ERRor?").strip()
        if error != "0, No error":
            print(f"PAX1000 Error: {error}")

        # Request the latest completed measurement
        data_str = self.device.query(":SENSe1:DATA:PRIMary:LATest?")
        data_list = data_str.strip().split(',')

        # Expecting 13 fields
        if len(data_list) >= 13:
            try:
                result = {
                    'timestamp': float(data_list[1]),
                    'mode': int(data_list[2]),
                    'flags': int(data_list[3]),
                    'range': int(data_list[4]),
                    'adc_min': float(data_list[5]),
                    'adc_max': float(data_list[6]),
                    'rev_time': float(data_list[7]),
                    'misalignment': float(data_list[8]),
                    'theta': float(data_list[9]),  # Related to 2θP
                    'eta': float(data_list[10]),   # Related to 2εB
                    'DOP': float(data_list[11]),   # Degree of Polarization
                    'power': float(data_list[12])  # Total power in W
                }
                return result
            except (ValueError, IndexError) as e:
                print(f"Error parsing polarimeter data: {e}")
                return None
        else:
            print("Incomplete data received from polarimeter")
            return None

    def close(self):
        """ Close the connection to the instrument. """
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()