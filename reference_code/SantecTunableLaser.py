import pyvisa

### Device class files
class TSL770:
    """
    Class to control Santec Tunable laser via USB serial connection
    """      
    def __init__(self, serial_port=9):
        """Initialize connection to Santec TSL770 Tunable Laser"""
        # For serial port connections, you need to install the USB driver first
        # Check TSL770 manual for installation of the driver
        # Driver is in the USB stick drive that was packaged together with the laser
        self.rm = pyvisa.ResourceManager()
        self.address = f"ASRL{serial_port}::INSTR"
        try:
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # timeout 5 seconds
            self.device.read_termination = "\r" # termination character
            
            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()} via Serial COM{serial_port}")
        except Exception as e:
            print(f"Error Connecting to TSL770: {e}")
            raise
        
    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()       
        
    """
    Basic operations
    """
    def power_unit(self, *unit):
        # Set the unit of laser power
        if len(unit) == 1:
            match unit[0]:
                case 'dBm':
                    u = '0'
                case 'mW':
                    u = '1'
            self.device.write("POWER:UNIT " + u)
        else:
            response = self.device.query("POWER:UNIT?")
            if response == '0':
                return "dBm"    
            elif response == '1':
                return "mW"

    def power(self, *p):
        # Set the laser power
        if len(p) == 1:
            self.device.write("POWER " + str(p[0]));
        else:
            response = self.device.query("POWER?")
            return response
            
    def shutter(self, *p):
        # 0 for shutter open, 1 for shutter closed
        # 'ACTIVE' button on the laser, green light if 0
        if len(p) == 1:
            self.device.write('POWER:SHUTTER ' + str(p[0]))
        else:
            response = self.device.query("POWER:SHUTTER?")
            return response        

    def wavelength_unit(self, *unit):
        # Set the unit of laser wavelength
        if len(unit) == 1:
            match unit[0]:
                case 'nm':
                    u = '0'
                case 'THz':
                    u = '1'
            self.device.write("WAVELENGTH:UNIT " + u)
        else:
            response = self.device.query("WAVELENGTH:UNIT?")
            if response == '0':
                return "nm"    
            elif response == '1':
                return "THz"

    def frequency(self, *f):
        # Set the laser optical frequency, unit is Hz
        # e.g. 1.9e+14 for 190 THz
        if len(f) == 1:
            self.device.write('FREQUENCY ' + str(f[0]))
        else:
            response = self.device.query("FREQUENCY?")
            return response         
    
    def wavelength(self, *w):
        # Set the laser wavelength, unit is meter
        # e.g. 1550e-9 for 1550nm
        if len(w) == 1:
            self.device.write('WAVELENGTH ' + str(w[0]))
        else:
            response = self.device.query("WAVELENGTH?")
            return response                    
    
       
    """
    Sweep functions
    """
    def wavelength_start(self, *w):
        # Set the start point of laser wavelength sweep, unit is meter
        # e.g. 1550e-9 for 1550nm
        if len(w) == 1:
            self.device.write('WAVELENGTH:SWEEP:START ' + str(w[0]))
        else:
            response = self.device.query("WAVELENGTH:SWEEP:START?")
            return response     

    def wavelength_stop(self, *w):
        # Set the stop point of laser wavelength sweep, unit is meter
        # e.g. 1550e-9 for 1550nm
        if len(w) == 1:
            self.device.write('WAVELENGTH:SWEEP:STOP ' + str(w[0]))
        else:
            response = self.device.query("WAVELENGTH:SWEEP:STOP?")
            return response     

    def sweep_speed(self, *s):
        # Set the sweep speed, unit is nm/s
        if len(s) == 1:
            self.device.write('WAVELENGTH:SWEEP:SPEED ' + str(s[0]));
        else:
            response = self.device.query("WAVELENGTH:SWEEP:SPEED?")
            return response  
        
    def sweep_state(self, *s):
        # set the sweep status
        # 0: stop,  1: start    
        if len(s) == 1:
            self.device.write('WAVELENGTH:SWEEP:STATE ' + str(s[0]));
        # read the sweep status
        # 0: stopped, 1: running, 3: standing by trigger, 4: preparation for sweep start
        else:
            response = self.device.query("WAVELENGTH:SWEEP:STATE?")
            return response  

    def sweep_mode(self, *mode):
        # set the sweep mode
        # 0:Step sweep mode and One way
        # 1:Continuous sweep mode and One way
        # 2:Step sweep mode and Two way
        # 3:Continuous sweep mode and Two way        
        if len(mode) == 1:
            self.device.write('WAVELENGTH:SWEEP:MODE ' + str(mode[0]));   
        else:
            response = self.device.query("WAVELENGTH:SWEEP:MODE?")
            return response             

    def trigger_setting(self, *mode):
        # set the trigger setting
        # 0 for wavelength-based trigger, 1 for time-based trigger,
        # which is somehow opposite to the manual...
        if len(mode) == 1:
            self.device.write('TRIGGER:OUTPUT:SETTING ' + str(mode[0]));   
        else:
            response = self.device.query("TRIGGER:OUTPUT:SETTING?")
            return response   

    def read_wavelength(self):
        #rawData = self.device.query(':READ:POIN?')
        rawData = self.device.query_binary_values(':READ:DAT?', datatype='d', is_big_endian=False, container=list)
        return rawData

    def trigger_step(self, *s):
        # set the step for wavelength-based trigger, unit is meter
        # note that there is a minimum trigger step size for given sweep speed
        # for instance,
        # 1 pm trigger step for 5nm/s sweep speed
        # 2 pm trigger step for 10nm/s sweep speed
        # 4 pm trigger step for 20nm/s sweep speed
        # Setting smaller trigger step does not impact the output trigger
        if len(s) == 1:
            self.device.write('TRIGGER:OUTPUT:STEP ' + str(s[0]))
        else:
            response = self.device.query("TRIGGER:OUTPUT:STEP?")
            return response   
        