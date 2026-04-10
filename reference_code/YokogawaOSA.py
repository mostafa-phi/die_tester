import pyvisa, time
import numpy as np


### Device class files
class AQ6374E:
    """
    Class to control AQ6374E Yokogawa Optical Spectrum Analyzer via GPIB connection
    """      
    def __init__(self, gpib_address=1):
        """Initialize connection to the Optical Spectrum Analyzer"""
        self.rm = pyvisa.ResourceManager()
        self.address = f"GPIB1::{gpib_address}::INSTR"
        try:
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # 5 seconds timeout
            self.device.write("*CLS")  # Clear status registers
            self.device.write("*RST")  # Reset to defaults
            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")
        except Exception as e:
            print(f"Error connecting to OSA: {e}")
            raise

    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()     

    def wavelength_start(self, *wav):
        # Start wavelength
        if len(wav) == 1:
            self.device.write(":SENS:WAV:STAR " + str(wav[0]))
        else:
            response = self.device.query(":SENS:WAV:STAR?")
            return float(response)    

    def wavelength_stop(self, *wav):
        # Stop wavelength
        if len(wav) == 1:
            self.device.write(":SENS:WAV:STOP " + str(wav[0]))
        else:
            response = self.device.query(":SENS:WAV:STOP?")
            return float(response)    

    def resolution(self, *bw):
        # Resolution
        if len(bw) == 1:
            self.device.write(":SENS:BAND " + str(bw[0]))
        else:
            response = self.device.query(":SENS:BAND?")
            return float(response)    

    def averaging(self, *num):
        # Set the number of averaging
        if len(num) == 1:
            self.device.write(":SENS:AVER:COUN " + str(num[0]))
        else:
            response = self.device.query(":SENS:AVER:COUN?")
            return float(response)    

    def sampling(self, *num):
        # Set the number of sampling points
        if len(num) == 1:
            self.device.write(":SENS:SWE:POIN " + str(num[0]))
        else:
            response = self.device.query(":SENS:SWE:POIN?")
            return float(response)    

    def sweep(self):
        # Initiate a wavelength sweep
        self.device.write(":INIT")    

    def stop(self):
        # Stop a wavelength sweep
        self.device.write(":ABOR")
        
    def sweep_mode(self, *m):
        # Set sweep mode
        # 1 = SINGLE
        # 2 = REPEAT
        # 3 = AUTO
        if len(m) == 1:
            self.device.write(":INIT:SMOD " + str(m[0]))
        else:
            response = self.device.query(":INIT:SMOD?")
            return float(response)

    def read(self):
        # Read wavelength and trace data
        wavelength = self.device.query_ascii_values(":TRAC:X? TRA")
        power = self.device.query_ascii_values(":TRAC:Y? TRA")
        return wavelength, power
