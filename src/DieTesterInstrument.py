from threading import Thread
import time
import numpy as np
import pyvisa
from typing import *
import matplotlib.pyplot as plt

from src.RealtimeVideoCapture import RealtimeVideoCapture
from src.InteractivePlots import *

SPEED_TABLE = { # (L, F, R, S) in units: pulses per second (pps), pps, msec, percentage.
    0: [10, 10, 1e-3, 0],
    1: [50, 50, 1e-3, 0],
    2: [100, 100, 1e-3, 0],
    3: [100, 500, 0.1, 0],
    4: [100, 1000, 0.1, 0],
    5: [100, 2000, 0.1, 0],
    6: [100, 5000, 0.1, 0],
    7: [1000, 10000, 0.1, 0],
    8: [1000, 20000, 0.1, 0],
    9: [1000, 50000, 0.1, 0]
}

DRIVER_DIVISION_SETTING = {  # pulses per micron for driver division setting
    0:  1,
    1:  2,
    2:  2.5,
    3:  4,
    4:  5,
    5:  8,
    6:  10,
    7:  20,
    8:  25,
    9:  40,
    10: 50,
    11: 80,
    12: 100,
    13: 125,
    14: 200,
    15: 250,
}

class SurugaSeikiDS102:
    """
    Class to control the Suruga Seiki DS102 Stepper Motor via USB
    """    
    default_speed = 9; # default speed
    default_step = 7; # Precision limit of our linear XYZ stages (50 nm / pulse)
    query_delay = 0.1 # you can actually query quite fast. Original value was 0.5.
    
    def __init__(self, address, stage_parity = [1, 1], origin_return_mode: Tuple[int, int] = (0, 0)):
        """
        Initialize connection to the stepper motor
            Origin return mode is a 2-element list setting how the stepper returns to (0,0). See manual for more, but recommended is '3' for CCW homing (towards motor) or '4' for CW homing (away from motor.)"
        """
        # For serial connections, you need to install .dll files first
        # These are available and you can download from the Suruga-Seiki website
        self.rm = pyvisa.ResourceManager()
        self.address = address
        self.driver_ppm = DRIVER_DIVISION_SETTING[self.default_step] # pulses per micron
        self.stage_parity = stage_parity # determines parity of X and Y axis movement according to our convention

        try:
            self.device = self.rm.open_resource(self.address, query_delay=self.query_delay) # add delay to query to account for usb delay
            self.device.timeout = 5000  # timeout 5 seconds
            self.device.read_termination = '\r' # termination character

            idn = self.device.query("*IDN?")
            print(f"Connected to: {idn.strip()}")

            # set default speed
            self.write(f"AXI1:SELSP {self.default_speed}")
            self.write(f"AXI2:SELSP {self.default_speed}")
            
            # set driver division setting
            self.write(f'AXI1:DRDIV {self.default_step}')
            self.write(f'AXI2:DRDIV {self.default_step}')

            # Set origin return mode (center homing)
            self.write(f"AXI1:MEMSW0 {origin_return_mode[0]}")
            self.write(f"AXI2:MEMSW0 {origin_return_mode[1]}") 
            
        except Exception as e:
            print(f"Error Connecting to Stepper Motor: {e}")
            raise
    @property
    def x(self):
        return self.query_position('X')
    @property
    def y(self):
        return self.query_position('Y')
    
    def stop(self, type='E'):
        """Emergency stop (or slowdown stop)
            type: 'E' or 'R', for emergency or slowdown respectively.
        """
        type = type.upper()
        assert type == 'E' or type == 'R', "Type of stop must be 'E' or 'R'."

        self.write(f'STOP {type}')
        return

    def wait_until_paused(self, motion_start_timeout=0.2):
        # Function to wait until all motion is complete
        start_time = time.time()

        in_motion = False
        motion_started = False
        while in_motion or not motion_started:
            in_motion = self.query_motion()
            if in_motion:
                motion_started = True
            if not motion_started and time.time() - start_time > motion_start_timeout: # For shorter motions, this means that motion already finished before our query.
                return

        return 

    def query_motion(self):
        """query device for motion"""
        motion = self.query("MOTION?")
        try: 
            motion_integer = int(motion)
            if motion_integer != 0 and motion_integer != 1:
                raise ValueError
        except ValueError:
            print(f"Return data has the wrong value! Expected 0 or 1, recieved {motion}.")
            raise ValueError
        except Exception as e:
            raise e

        return motion_integer
    
    def axstr(self, axis):
        axis = axis.upper()
        if  axis == 'X':
            axstr = 'AXI1'; parity = self.stage_parity[0]
        elif axis == 'Y':
            axstr = 'AXI2'; parity = self.stage_parity[1]
        else:
            raise ValueError("Invalid axis! Must be X or Y.")
        
        return axstr, parity

    def query_position(self, axis):
        """Query device for the position of an axis ('X' or 'Y') in microns."""
        axstr, parity = self.axstr(axis)
        
        pos = self.query(f"{axstr}:POS?")
        try: 
            micron_pos = int(pos) / self.driver_ppm * parity

        except ValueError:
            print(f"Return data has the wrong value! Expected an integer, recieved {pos}.")
        except Exception as e:
            raise e
        
        return micron_pos

    def initialize(self):
        """Initialize the position of both axes. Warning: This will home the axes. Make sure they won't collide into anything."""
        self.set_speed(self.default_speed)
        self.write("AXI1:GO ORG")
        self.write("AXI2:GO ORG")

        return

    def set_speed(self, speed):
        """Set speed for both axes. (Device doesn't seem to work with single-axis speed selection.)"""
        self.write(f'AXI1:SELSP {speed}')
        self.write(f'AXI2:SELSP {speed}')

        return
    
    def move_relative(self, axis, distance, wait=False):
        """Move the stage by a distance in microns along an axis."""

        num_pulses = int(round( self.driver_ppm * np.abs(distance) )) # convert microns to pulses
        axis = axis.upper()  # make sure axis is uppercase
        try:
            axstr, parity = self.axstr(axis)
            #print(parity)
            #print(self.stage_parity)
            
            if distance * parity < 0:
            #if distance < 0:
                dirstr = '-'
            else:
                dirstr = '+'
    
            cmd = f"{axstr}:PULS {num_pulses}:GOLI {axis}{dirstr}"
            self.write(cmd)
        except Exception as e:
            print(f"Stage movement failed: {e}")
            raise e
        
        if wait:
            self.wait_until_paused()

    def move_absolute(self, pos, wait=False):
        """Move the stage to an absolute position in microns, or 'None' to avoid modifying position for that axis. """        
        if pos[0] is None:
            xstr = ""
        else:
            pulseX = int(round( self.driver_ppm * pos[0] )) # convert microns to pulses
            xstr = f" X{pulseX * self.stage_parity[0]}"

        if pos[1] is None:
            ystr = ""
        else:
            pulseY = int(round( self.driver_ppm * pos[1] ))
            ystr = f" Y{pulseY * self.stage_parity[1]}"
        
        try:
            cmd = f"GOLA {xstr}{ystr}"
            self.write(cmd)
        except Exception as e:
            print(f"Stage movement failed: {e}")
            raise e
            
        if wait:
            self.wait_until_paused()
        
        return

    def query(self, string):
        # passthrough function
        return self.device.query(string)
    
    def write(self, string, sleep=True):
        # Passthrough function with sleep
        self.device.write(string)
        time.sleep(self.query_delay)

    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()

class DieTesterCenterStage(SurugaSeikiDS102):

    degrees_per_micron = 0.006 / 1  # Number of degrees per full-step pulse (one micron) according to website 

    def __init__(self, address, raxis, **kwargs):
        super().__init__(address, **kwargs)
        assert raxis.upper() == 'X' or raxis.upper() == 'Y', "Rotational axis must be 'X' or 'Y'."

        self.raxis = raxis.upper()
        self.xaxis = 'X' if raxis == 'Y' else 'Y'

        # Disable rotational axis's limit switch.
        axstr, _ = self.axstr(self.raxis)
        self.write(f"{axstr}:MEMSW1 1")
        self.write(f"{axstr}:MEMSW2 0")

    @property
    def x(self):
        return self.query_position(self.xaxis)
    @property
    def r(self):
        return self.query_position(self.raxis)

    def move_absolute(self, xpos=None, rpos=None, wait=False):
        "Move to an absolute position in x: microns, r: degrees."
        if rpos is not None:
            rpos = rpos / self.degrees_per_micron 
    
        if self.raxis == 'X':
            super().move_absolute((rpos, xpos), wait=wait)
        elif self.raxis == 'Y':
            super().move_absolute((xpos, rpos), wait=wait)
        else:
            raise ValueError("Rotational axis string doesn't match? Check your functions.")
        return 
    
    def move_relative_r(self, deg, wait=False):
        micron_distance = deg / self.degrees_per_micron
        super().move_relative(self.raxis, micron_distance, wait=wait)
        return
    
    def move_relative_x(self, distance, wait=False):
        super().move_relative(self.xaxis, distance, wait=wait)
        return 

    def query_position(self, axis):
        if axis == self.raxis:  # Return position in degrees
            return super().query_position(axis) * self.degrees_per_micron
        elif axis == self.xaxis:  # Return position in microns
            return super().query_position(axis)
        else:
            raise ValueError("Invalid axis! Must be X or Y.")


class DieTesterStage:
    """
    Class to control the die tester stage
    """        
    
    def __init__(self, com1, com2, com3, com4, raxis='Y'):
        # Serial port index COM_
        # Check the COM index of each motor controller from device manager
        # Origin return modes: '3' Means CCW, or towards motor, '4' means CW, which means away from motor.
        #   This means that X-axis is towards motor (and human), Y-axis is downwards, Z-axis is away from the waveguide.
        #   DO NOT CHANGE Z ORIGIN RETURN UNLESS YOU KNOW WHAT YOU ARE DOING (setting it to '4' could crash the fibers into the waveguide, for instance.)
        self.dev1 = SurugaSeikiDS102(f"ASRL{com1}::INSTR", stage_parity = (1, -1),  origin_return_mode = (3, 4))                    # #1, Left-XY
        self.dev2 = SurugaSeikiDS102(f"ASRL{com2}::INSTR", stage_parity = (1, -1), origin_return_mode = (3, 4))                   # #2, Right-XY
        self.dev3 = DieTesterCenterStage(f"ASRL{com3}::INSTR", raxis=raxis, stage_parity = (1, 1), origin_return_mode = (3, 3))     # #3, Middle-X and Rotation
        self.dev4 = SurugaSeikiDS102(f"ASRL{com4}::INSTR", stage_parity = (1,  1), origin_return_mode = (3, 3))                    # #4, Z-axis 
    
    def initialize(self):
        """Initialize stages to the origin and set (0,0). Warning: This will home the axes. Make sure they won't collide into anything."""
        # Initialize all stepper motors to zero position simultaneously
        threads = [
            Thread(target=self.dev1.initialize),
            Thread(target=self.dev2.initialize),
            Thread(target=self.dev3.initialize),
            Thread(target=self.dev4.initialize),   
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.dev1.wait_until_paused()
        self.dev2.wait_until_paused()
        self.dev3.wait_until_paused()
        self.dev4.wait_until_paused()

    def allocation(self, stage):
        # allocate each axis of stepper motor to controller
        # stage:
        #   'l' is the upstream of the sample
        #   'm' is the sample
        #   'r' is the downstream of the sample
        # direction:
        #   'x' is along the propagation axis (waveguide)
        #   'y' is in-plane, perpendicular to x
        #   'z' is out-of-plane

        # Here you may want to change the convention of x, y, z; (can change by modifying 'stage_parity' in initalization.)
        # Our convention for both upstream and downstream is,
        # +z: along the waveguide propagation, towards the sample
        # +y: out-of-plane dimension of the chip (thus sample mount), upward
        # +x: transverse dimension, determined by +z and +y
        # On the sample stage, +x moves towards the camera gantry (same as left stage)
        match stage.lower():
            case 'l':
                dev_xy = self.dev1; dev_z = self.dev4; z_axis = 'X'
            case 'r':
                dev_xy = self.dev2; dev_z = self.dev4; z_axis = 'Y'
            case 'm':
                dev_xy = self.dev3; dev_z = None     ; z_axis = None
            case _:
                raise Exception("Invalid stage selection!")

        return dev_xy, dev_z, z_axis
    
    def stop(self):
        """Emergency stop for all stages and axes."""
        self.dev1.stop()
        self.dev2.stop()
        self.dev3.stop()
        self.dev4.stop()
        return
    
    def close(self):
        """Close connection to all devices"""
        self.dev1.close()
        self.dev2.close()
        self.dev3.close()
        self.dev4.close()
        print("All stepper motors disconnected")

    def set_speed(self, stage, speed: int):
        """Set speed for a stage."""
        dev_xy, dev_z, _ = self.allocation(stage)
        
        dev_xy.set_speed(speed)
        if dev_z is not None:
            dev_z.set_speed(speed) # have to set both Z-axes with this speed, because controller doesn't seem to support single axis speed
        
        return
    
    def query_position(self, stage):
        """Query the current absolute position of the left, right, or center stage."""
        dev_xy, dev_z, z_axis = self.allocation(stage)

        if isinstance(dev_xy, DieTesterCenterStage):
            return (dev_xy.x, dev_xy.r)  # (X, R)
        else:
            return (dev_xy.x, dev_xy.y, dev_z.query_position(z_axis))  # (X, Y, Z)
    
    def move_relative_rotation(self, degrees, wait=False):
        dev_xy, _, _ = self.allocation('m')
        dev_xy.move_relative_r(degrees, wait=wait)

    def move_relative(self, stage, axis, distance, wait=False):
        """
        Move relatively along an axis.
            stage: 'l', 'm', or 'r'
            axis: 'X', 'Y', 'Z'
            distance: distance in microns
        """
        stage = stage.lower() # set proper case just for redundancy
        axis = axis.upper()
        dev_xy, dev_z, z_axis = self.allocation(stage)

        ## Middle Stage
        if isinstance(dev_xy, DieTesterCenterStage):
            if axis != 'X':
                raise ValueError("Middle stage has no 'Y' or 'Z' axis; if you're trying to rotate, use the move_relative_rotation command.")
            
            dev_xy.move_relative_x(distance, wait=wait)
            return

        
        ## Left or right stages
        dev_xy, dev_z, z_axis = self.allocation(stage)
        match axis: # make sure distance is the right direction for the motor, then move.
            case 'X':
                dev_xy.move_relative(axis, distance, wait=wait)
            case 'Y':
                dev_xy.move_relative(axis, distance, wait=wait)
            case 'Z':
                dev_z.move_relative(z_axis, distance, wait=wait)
            case _:
                raise ValueError(f"Invalid axis selection of '{axis}'!")
        
        
    def move_absolute(self, stage, x=None, y=None, z=None, r=None, wait=False):
        """
        Move absolutely to a x,y,z coordinate for left and right stages, or x,r for center stage (r is in degrees).
            stage: 'l', 'm', or 'r'
            for x,y,z inputs: Values of 'None' will maintain their current absolute position
        """

        stage = stage.lower() # set proper case just for redundancy
        dev_xy, dev_z, z_axis = self.allocation(stage)

        ## Middle Stage
        if isinstance(dev_xy, DieTesterCenterStage):
            if not (z is None and y is None):
                raise ValueError("The center stage does not have a Z-axis or Y-axis.")

            dev_xy.move_absolute(x, r, wait=wait)
            return

        ## Left or right stages
        # Simultaneous movement for xy and z axes (this only works because xy and z are two separate devices)
        threads = []

        if not r is None:
            raise ValueError("The left and right stages do not have a R-axis.")
    
        # If moving Z, then append proper movement to threads.
        if not z is None:
            if z_axis == 'X':
                z_thread = Thread(target=dev_z.move_absolute, args=[(z, None)], kwargs={"wait": wait}) # leave unused motor at 'None' to keep current position of second stepper ('GOLA X0 Y' is equivalent to 'GOLA X0')
            elif z_axis == 'Y':
                z_thread = Thread(target=dev_z.move_absolute, args=[(None, z)], kwargs={"wait": wait})
            threads.append(z_thread)

        # If moving either X or Y, then append proper movement to threads.
        if not (x is None and y is None):
            xy_thread = Thread(target=dev_xy.move_absolute, args=[(x, y)], kwargs={"wait": wait})
            threads.append(xy_thread)

        for t in threads:
            t.start()
        for t in threads:
            t.join()