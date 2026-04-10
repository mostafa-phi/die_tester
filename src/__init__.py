import clr 

THORLABS_PATH = "C:\\Program Files\\Thorlabs"

clr.AddReference(f"{THORLABS_PATH}\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference(f"{THORLABS_PATH}\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference(f"{THORLABS_PATH}\\Kinesis\\ThorLabs.MotionControl.KCube.DCServoCLI.dll")

# Elliptec is for the alternative Thorlabs rotational
# clr.AddReference(f'{THORLABS_PATH}\\Elliptec\\Thorlabs.Elliptec.ELLO_DLL.dll')