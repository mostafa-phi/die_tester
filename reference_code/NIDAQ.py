import nidaqmx, time

### Device class files
class USB6363:
    """
    Class to control USB6363 NI Data Acquisition Board via USB serial connection
    """      
    def __init__(self):
        """Initialize connection to NI DAQ board"""
        try:
            system = nidaqmx.system.System.local()
            for device in system.devices:
                self.device_name = device.name
            print('Connected to: NI DAQ, {0}, {1}'.format(device.name, device.product_type))
        except Exception as e:
            print(f"Error Connecting to NI DAQ: {e}")
            raise
        self.ai_task = []
        self.di_task = []
        self.sample_rate = 1e3 # Hz
        self.Nsample = int(1e3) # number of samples

    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()     

    def add_digitalInput(self, channel):
        try:
            self.di_task = nidaqmx.Task()
            self.di_task.di_channels.add_di_chan(self.device_name + "/" + channel)
        except Exception as e:
            print(f"Error Adding an Digital Input Channel: {e}")
            raise            

    def add_analogInput(self, channel):
        try:
            self.ai_task = nidaqmx.Task()
            self.ai_task.ai_channels.add_ai_voltage_chan(self.device_name + "/" + channel)
        except Exception as e:
            print(f"Error Adding an Analog Input Channel: {e}")
            raise    

    def configure_sampling(self, sample_rate, Nsample):
        try:
            self.sample_rate = sample_rate
            self.Nsample = int(Nsample)
            # configure digital/analog input channels sharing the same clock
            if self.ai_task:
                self.ai_task.timing.cfg_samp_clk_timing(self.sample_rate, source=None, sample_mode=nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan=self.Nsample)
            if self.di_task:
                self.di_task.timing.cfg_samp_clk_timing(self.sample_rate, source="ai/SampleClock", sample_mode=nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan=self.Nsample)
        except Exception as e:
            print(f"Error Configuring the Sampling: {e}")
            raise 

    def start(self):
        # Start tasks, please keep the starting order of digital and then analog channels
        try:
            if self.di_task:
                self.di_task.start()
            #t_d = 0.2; time.sleep(t_d) # Sanity check to see if digital/analog input channels sharing the same clock in presence of delay
            if self.ai_task:
                self.ai_task.start()
        except Exception as e:
            print(f"Error Starting the tasks: {e}")
            raise     

    def read(self):
        # Read data
        Data = []
        try:
            if self.ai_task:
                rawdata = self.ai_task.read(number_of_samples_per_channel = self.Nsample, timeout=-1)
                Data.append(rawdata)
            if self.di_task:
                rawdata = self.di_task.read(number_of_samples_per_channel = self.Nsample, timeout=-1)
                Data.append(rawdata)
            return Data
        except Exception as e:
            print(f"Error Reading the tasks: {e}")
            raise  

    def stop(self):
        # Stop tasks       
        try:
            if self.ai_task:
                self.ai_task.stop()
            if self.di_task:
                self.di_task.stop()   
        except Exception as e:
            print(f"Error Stopping the tasks: {e}")
            raise    
