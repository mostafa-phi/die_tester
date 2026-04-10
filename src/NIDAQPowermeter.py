import nidaqmx
from nidaqmx.constants import AcquisitionType, LineGrouping, ProductCategory
import nidaqmx.stream_readers

class PowermeterSystem:  # USB6363 system comprising of power meter and cnt-i/o for the left and right xy stages.
    """
    Class to control USB6363 NI Data Acquisition Board via USB serial connection
    """
    def __init__(self, device_name, sample_rate, ai_channel): #, ai_channel
        """Initialize connection to NI DAQ board"""
        system = nidaqmx.system.System.local()
        self.device_object = nidaqmx.system.Device(name=device_name) # make device
        assert self.device_object in system.devices, f"Device was not found on the system. Available devices: {list(system.devices)}."

        self.device_name = device_name
        self.sample_rate = sample_rate
        self.channel_id = ai_channel
        self.pow_task = self.setup_power_task() # power task
        self.mot_task = self.setup_motion_task() # motion task
        self.pow_reader =  nidaqmx.stream_readers.AnalogSingleChannelReader(self.pow_task.in_stream)
        self.mot_reader =  nidaqmx.stream_readers.DigitalSingleChannelReader(self.mot_task.in_stream)
        print('Connected to: NI DAQ, {0}, {1}'.format(self.device_object.name, self.device_object.product_type))
    
    def setup_power_task(self): # ai_channel='ai0'
        "Setup function for the powermeter. Contains analog powermeter channel and several motion detection channels."
        task = nidaqmx.Task()
        task.ai_channels.add_ai_voltage_chan(f'{self.device_name}/{self.channel_id}')
        # to have multiple channels
        # task.ai_channels.add_ai_voltage_chan(f'{self.device_name}/{self.channel_id[0]}, {self.device_name}/{self.channel_id[1]}, {self.device_name}/{self.channel_id[2]}, {self.device_name}/{self.channel_id[3]}')
        task.timing.cfg_samp_clk_timing(self.sample_rate, sample_mode=AcquisitionType.CONTINUOUS)
        print(task.ai_channels[0])
        return task
    
    def setup_motion_task(self, di_channel='port0'):
        task = nidaqmx.Task()
        task.di_channels.add_di_chan(f'{self.device_name}/{di_channel}', line_grouping=LineGrouping.CHAN_FOR_ALL_LINES) # 32 total lines
        task.timing.cfg_samp_clk_timing(self.sample_rate, sample_mode=AcquisitionType.CONTINUOUS)

        return task     
    
    def start(self):
        self.pow_task.start()
        self.mot_task.start()

    def stop(self):
        self.pow_task.stop()
        self.mot_task.stop()

    def close(self): 
        self.pow_task.close()
        self.mot_task.close()

    def read(self, pow_buffer, mot_buffer, num_samples):
        """Read n samples from the device and write to preallocated 1d numpy arrays of the shape (n,)."""

        self.pow_reader.read_many_sample(pow_buffer, num_samples)
        self.mot_reader.read_many_sample_port_uint32(mot_buffer, num_samples)

        return

