import pyvisa, time

### Device class files
class SurugaSeikiDS102:
    """
    Class to control the Suruga Seiki DS102 Stepper Motor via USB
    """    
    speed = 9; # default speed
    
    def __init__(self, address):
        """Initialize connection to the stepper motor"""
        # For serial connections, you need to install .dll files first
        # These are available and you can download from the Suruga-Seiki website
        self.rm = pyvisa.ResourceManager()
        self.address = address
        try:
            
            self.device = self.rm.open_resource(self.address)
            self.device.timeout = 5000  # timeout 5 seconds
            self.device.read_termination = '\r' # termination character
            
            idn = self.device.query("*IDN?")
            time.sleep(0.5)
            print(f"Connected to: {idn.strip()}")
            
            time.sleep(0.5); # somehow the reponse of controller is slow thus delay needed
            self.device.write(f"AXI1:SELSP {self.speed}")
            time.sleep(0.5);
            self.device.write(f"AXI2:SELSP {self.speed}")
            
            """
            time.sleep(0.5);
            idn = self.device.query("AXI1:SELSP?")
            print(f"AXIS 1 Motor Speed is set up to {idn.strip()}")
            time.sleep(0.5);
            idn = self.device.query("AXI2:SELSP?")
            print(f"AXIS 2 Motor Speed is set up to {idn.strip()}")
            """
        except Exception as e:
            print(f"Error Connecting to Stepper Motor: {e}")
            raise
    
    def move(self, axis, distance):
        """Move the stage by a distance along an axis"""
        try:
            
            if distance != round(distance):
                raise Exception('Put an integer number of steps')
                
            if axis == 'X':
                axstr = 'AXI1'
            elif axis == 'Y':
                axstr = 'AXI2'
                
            if distance < 0:
                dirstr = '-'
            else:
                dirstr = '+'
                
            cmd = axstr+':PULS '+str(abs(distance))+':GOLI '+axis+dirstr
            
            self.device.write(cmd)
            
            motionComplete = 0;
            while not motionComplete: # Check if the motion is complete
                time.sleep(0.5);
                q = self.device.query('MOTION?')
                motionComplete = not int(q)
            
        except Exception as e:
            print(f"Stage movement failed: {e}")
            raise

    def initialize(self):
        """Initialize the position of stepper motors for both axes"""
        self.device.write('AXI1:GOABS 0')
        time.sleep(0.5);
        self.device.write('AXI2:GOABS 0')    
        
        motionComplete = 0;
        while not motionComplete: # Check if the motion is complete
            time.sleep(0.5);
            q = self.device.query('MOTION?')
            motionComplete = not int(q)
        
    def close(self):
        """Close the connection to the instrument"""
        if hasattr(self, 'device'):
            self.device.close()
        if hasattr(self, 'rm'):
            self.rm.close()
            
            
class DieTesterStage:
    """
    Class to control the die tester stage
    """        
    conversion = 20; # conversion factor for argument of move function in micron
    
    def __init__(self, com1=5, com2=7, com3=8, com4=6):
        # Serial port index COM_
        # Check the COM index of each motor controller from device manager
        self.dev1 = SurugaSeikiDS102(com1) # #1, Left-XY
        self.dev2 = SurugaSeikiDS102(com2) # #2, Right-XY
        self.dev3 = SurugaSeikiDS102(com3) # #3, Middle-XY
        self.dev4 = SurugaSeikiDS102(com4) # #4, Z-axis
    
    def initialize(self):
        # Initialize all stepper motors to zero position
        self.dev1.initialize()
        self.dev2.initialize()
        self.dev3.initialize()
        self.dev4.initialize()
        
    def allocation(self, stage, direction):
        # allocate each axis of stepper motor to controller
        # stage:
        #   'l' is the upstream of the sample
        #   'm' is the sample
        #   'r' is the downstream of the sample
        # direction:
        #   'x' is along the propagation axis (waveguide)
        #   'y' is in-plane, perpendicular to x
        #   'z' is out-of-plane
        match stage+direction:
            case 'lx':
                dev = self.dev1; axis = 'X';
            case 'ly':
                dev = self.dev1; axis = 'Y';
            case 'lz':
                dev = self.dev3; axis = 'X';
            case 'rx':
                dev = self.dev2; axis = 'X';
            case 'ry':
                dev = self.dev2; axis = 'Y';
            case 'rz':
                dev = self.dev3; axis = 'Y';
            case 'mx':
                dev = self.dev4; axis = 'X';
            case 'my':
                dev = self.dev4; axis = 'Y';
        return dev, axis
    
    def close(self):
        self.dev1.close()
        self.dev2.close()
        self.dev3.close()
        self.dev4.close()
        print("All stepper motors disconnected")
            
        
    # Here you may want to change the convention of x, y, z
    # Our convention for both upstream and downstream is,
    # +z: along the waveguide propagation, towards the sample
    # +y: out-of-plane dimension of the chip (thus sample mount), upward
    # +x: transverse dimension, determined by +z and +y
    def lz(self, distance):
        dev, axis = self.allocation('l','x')
        dev.move(axis, round(self.conversion * distance))

    def lx(self, distance):
        dev, axis = self.allocation('l','y')
        dev.move(axis, round(self.conversion * distance))       

    def ly(self, distance):
        dev, axis = self.allocation('l','z')
        dev.move(axis, -round(self.conversion * distance))  

    def rz(self, distance):
        dev, axis = self.allocation('r','x')
        dev.move(axis, round(self.conversion * distance))  

    def rx(self, distance):
        dev, axis = self.allocation('r','y')
        dev.move(axis, -round(self.conversion * distance)) 

    def ry(self, distance):
        dev, axis = self.allocation('r','z')
        dev.move(axis, -round(self.conversion * distance))

    def mz(self, distance):
        dev, axis = self.allocation('m','x')
        dev.move(axis, round(self.conversion * distance))

    def mx(self, distance):
        dev, axis = self.allocation('m','y')
        dev.move(axis, round(self.conversion * distance)) 
