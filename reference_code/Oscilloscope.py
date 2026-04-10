import pyvisa, time
import numpy as np


class KeysightScope:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()

    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()

    """Define basic operations shared by various models of Keysight oscilloscopes"""

    """Basic operations"""
    def run(self):
        self.device.write(":RUN")

    def stop(self):
        self.device.write(":STOP")

    def single(self):
        self.device.write(":SINGLE")


    """Channel setting"""
    def display(self, channel, *f):
        # Display the channel
        if len(f) == 1:
            self.device.write(":CHAN" + str(channel) + ":DISP " + str(f[0]))
        else:
            response = self.device.query(":CHAN" + str(channel) + ":DISP?")
            return float(response)

    def offset(self, channel, *o):
        # Set the offset value, unit is Volt
        if len(o) == 1:
            self.device.write(":CHAN" + str(channel) + ":OFFS " + str(o[0]), ' V')
        else:
            response = self.device.query(":CHAN" + str(channel) + ":OFFS?")
            return float(response)  
        
    def vscale(self, channel, *s):
        # Set the single vertical division scale, unit is Volt
        if len(s) == 1:
            self.device.write(":CHAN" + str(channel) + ":SCAL " + str(s[0]))
        else:
            response = self.device.query(":CHAN" + str(channel) + ":SCAL?")
            return float(response)
        
    def autoscale(self, channel):
        # Automatically set the scale to display the signal
        self.device.write(":AUT" + str(channel))
                

    """Horizontal (time) setting"""
    def timepos(self, *pos):
        # Set the horizontal reference point, unit is second
        if len(pos) == 1:
            self.device.write(":TIM:POS " + str(pos[0]))
        else:
            response = self.device.query(":TIM:POS?")
            return float(response)
        
    def tscale(self, *s):
        # Set the single horizontal division scale, unit is second
        if len(s) == 1:
            self.device.write(":TIM:SCAL " + str(s[0]))
        else:
            response = self.device.query(":TIM:SCAL?")
            return float(response)

    def tstep(self):
        dt = float(self.device.query(":WAV:XINC?"))
        return dt


class EXR604A(KeysightScope):
    """
    Class to control the mixed signal oscilloscope Keysight EXR604A
    """

    def __init__(self):
        """Initialize connection to the scope"""
        self.rm = pyvisa.ResourceManager()
        self.address = "USB0::0x2A8D::0x9008::MY62460102::INSTR" # replace with the actual address
        try:
            
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # timeout 5 seconds

            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")

            self.device.write("*RST") # Reset the instrument
            self.device.write("*CLS") # Clear any existing errors
        
        except Exception as e:
            print(f"Error Connecting to Scope interface: {e}")
            raise
        
    def coupling(self, ch, *c):
        # Set the impedance and coupling
        if len(c) == 1:
            match str(c[0]):
                case "DC": # 1 MOhm
                    self.device.write(":CHAN" + str(ch) + ":INP DC")
                case "AC": # 1 MOhm
                    self.device.write(":CHAN" + str(ch) + ":INP AC")
                case "50": # 50 Ohm, DC
                    self.device.write(":CHAN" + str(ch) + ":INP DC50")
                case _:
                    print("The command should be DC / AC / 50")
        else:
            response = self.device.query(":CHAN" + str(ch) + ":INP?")
            return float(response)                
    
    ### Acquisition Settings
    def analogSamplingRate(self, *sr):
        # Set the analog sampling rate, unit: Samples/s
        if len(sr) == 1:
            self.device.write(":ACQ:SRAT:ANAL " + str(sr[0]))
        else:
            response = self.device.query(":ACQ:SRAT:ANAL?")
            return float(response)       

    def digitalSamplingRate(self, *sr):
        # Set the digital sampling rate, unit: Samples/s
        if len(sr) == 1:
            self.device.write(":ACQ:SRAT:DIG " + str(sr[0]))
        else:
            response = self.device.query(":ACQ:SRAT:DIG?")
            return float(response)  

    def analogMemoryDepth(self, *md):
        # Set the analog memory depth, unit: points
        if len(md) == 1:
            self.device.write(":ACQ:POIN:ANAL " + str(md[0]))
        else:
            response = self.device.query(":ACQ:POIN:ANAL?")
            return float(response)

    def adc(self, *res):
        # Set the ADC resolution
        if len(res) == 1:
            match res[0]:
                case "10Bits":
                    restr = "BITS10"
                case "11Bits":
                    restr = "BITS11"
                case "12Bits":
                    restr = "BITS12"
                case "13Bits":
                    restr = "BITS13"
                case "14Bits":
                    restr = "BITS14"
                case "15Bits":
                    restr = "BITS15"
                case "16Bits200MSa":
                    restr = "BITS16"
                case "16Bits100MSa":
                    restr = "BITS16_4"    
                case "16Bits50MSa":
                    restr = "BITS16_2"                                                                         
            self.device.write(":ACQ:ADCR " + str(restr))
        else:
            response = self.device.query(":ACQ:ADCR?")
            return response

    def averaging(self, *f):
        # analog averaging or not: 1 (ON) 0 (OFF)
        if len(f) == 1:
            self.device.write(":MTES:AVER " + str(f[0]))
        else:
            response = self.device.query(":MTES:AVER?")
            return float(response)        

    def averaging_number(self, *c):
        # if analog averaging is enabled, how many waveforms are averaged
        if len(c) == 1:
            self.device.write(":MTES:AVER:COUN " + str(c[0]))
        else:
            response = self.device.query(":MTES:AVER:COUN?")
            return float(response)      

    def acquisition(self):
        # Start acquisition of activated channels
        try:
            #t = self.tscale()
            self.device.write(":DIG")
            #time.sleep(15*t) # wait for sufficiently long time until acquisition ends
        
        except Exception as e:
            print(f"Error in Acquisition: {e}")
            raise   

    def read(self, channel):
        # After acquisition, read the data in each channel
        try:
            self.device.write(":WAV:FORM WORD") # use WORD (16 bit) instead of BYTE (8 bit)
            self.device.write(":WAV:SOUR CHAN" + str(channel))
            self.device.write(':WAV:DATA?')
            rawData = self.device.read_raw()

            # Process the raw data to signed integer format
            numByte = int(rawData[2:10]) # number of bytes read, should be twice of sampling points
            Data_Byte = np.array( list( rawData[11:-1] ) ) # exclude the header
            LSB = Data_Byte[2::2]
            MSB = Data_Byte[1::2]
            sign = np.array([1 if msb < 128 else -1 for msb in MSB])
            MSB_signed = MSB + (sign - 1)*128
            Data_Word = MSB_signed*256 + LSB
                    
            # Convert to analog voltage
            Y_or = float(self.device.query(":WAV:YOR?"))
            Y_inc = float(self.device.query(":WAV:YINC?"))
            Y_ref = float(self.device.query(":WAV:YREF?"))
            V = (Data_Word - Y_ref) * Y_inc + Y_or

            return V

        except Exception as e:
            print(f"Error in Read: {e}")
            raise          



class DSOX1204A(KeysightScope):
    """
    Class to control the Digital Oscilloscope Keysight DSOX1204A
    """
    
    def __init__(self):
        """Initialize connection to the scope"""
        self.rm = pyvisa.ResourceManager()
        self.address = "USB0::0x2A8D::0x0386::CN63176574::INSTR" # replace with the actual address
        try:
            
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # timeout 5 seconds

            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")

            self.device.write("*RST") # Reset the instrument
            self.device.write("*CLS") # Clear any existing errors
        
        except Exception as e:
            print(f"Error Connecting to Scope interface: {e}")
            raise


    def bandwidth(self, channel, *bw):
        # Set the bandwidth of low-pass filter, unit is Hz, e.g. 25 MHz: 25e6
        if len(bw) == 1:
            self.device.write(":CHAN" + str(channel) + ":BAND " + str(bw[0]))
        else:
            response = self.device.query(":CHAN" + str(channel) + ":BAND?")
            return float(response)    

    def attenuation(self, channel, *a):
        # Set the probe attenuation factor
        if len(a) == 1:
            self.device.write(":CHAN" + str(channel) + ":PROB " + str(a[0]))
        else:
            response = self.device.query(":CHAN" + str(channel) + ":PROB?")
            return float(response)        
        
    """Data acquisition"""
    def num_sample_pts(self, *npts):
        # Set the number of sampling points
        self.stop()
        if len(npts) == 1:
            # Following settings are needed for number of points more than 62500
            self.device.write(":TIM:MODE MAIN")
            self.device.write(":WAV:FORM BYTE") # 8-bit, sufficient for Keysight DSOX1204A
            self.device.write(":WAV:POIN:MODE RAW")
            self.device.write(":WAV:POIN " + str(int(npts[0])))
        else:
            self.device.write(":WAV:SOUR CHAN1") # any default channel
            response = self.device.query(":WAV:POIN?")
            return int(response)

    def acquisition(self):
        # Start acquisition of activated channels
        try:
            #t = self.tscale()
            self.device.write(":DIG")
            #time.sleep(15*t) # wait for sufficiently long time until acquisition ends
        
        except Exception as e:
            print(f"Error in Acquisition: {e}")
            raise
        
    def read(self, channel):
        # After acquisition, read the data in each channel
        try:
            self.device.write(":WAV:SOUR CHAN" + str(channel))
            self.device.write(':WAV:DATA?')
            rawData = self.device.read_raw()
            numByte = int(rawData[2:10]) # number of bytes read = in byte format, same as number of datapoints
            Data = list(rawData[11:-1]) # except the header

            # Digitized string to voltage
            Y_or = float(self.device.query(":WAV:YOR?"))
            Y_inc = float(self.device.query(":WAV:YINC?"))
            Y_ref = float(self.device.query(":WAV:YREF?"))
            V = (np.array(Data) - Y_ref) * Y_inc + Y_or

            return V

        except Exception as e:
            print(f"Error in Read: {e}")
            raise            