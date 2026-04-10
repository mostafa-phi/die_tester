import logging
import time
import re
from enum import Enum
from typing import Optional, List

import pyvisa
import numpy as np # Added for analysis later
import matplotlib.pyplot as plt # Added for plotting later

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Enums and Exceptions (same as before) ---
class PowerUnit(Enum):
    DBM = "DBM"
    W = "W"

class LaserError(Exception):
    pass

# --- MinimalN777C Class (same as previous version with lambda logging) ---
class N7776C:
    """
    driver for Keysight N7776C Tunable Laser Source.
    (Includes laser state, power, wavelength, continuous sweep, lambda logging)
    """
    def __init__(self, resource_address: str, timeout_ms: int = 10000):
        self.resource_address = resource_address
        self.resource = None
        self._last_error = None
        self._idn = None
        try:
            log.info(f"Connecting to N7776C at {resource_address}...")
            rm = pyvisa.ResourceManager()
            self.resource = rm.open_resource(resource_address)
            self.resource.timeout = timeout_ms
            self.resource.read_termination = '\n'
            self.resource.write_termination = '\n'
            self._idn = self._query("*IDN?")
            log.info(f"Connected to: {self._idn}")
            if "N7776C" not in self._idn:
                 log.warning(f"Instrument IDN '{self._idn}' does not contain 'N7776C'.")
            self._check_error()
            self._write(":TRIG0:OUTP STF") # Default trigger for LLOG
            log.info("Defaulted trigger output to STF for LLOG compatibility.")
            log.info("N7776C connection established.")
        except pyvisa.Error as e:
            log.error(f"VISA error connecting to {resource_address}: {e}")
            raise LaserError(f"VISA connection failed: {e}") from e
        except Exception as e:
            log.error(f"Unexpected error connecting: {e}")
            if self.resource: self.resource.close()
            raise LaserError(f"Unexpected connection error: {e}") from e

    def _write(self, command: str) -> None:
        if not self.resource: raise LaserError("Instrument resource is not connected.")
        log.debug(f"WRITE: {command}")
        try:
            self.resource.write(command)
            self._check_error(command)
        except pyvisa.VisaIOError as e:
            log.error(f"VISA Write Error on '{command}': {e}")
            raise LaserError(f"VISA Write Error: {e}") from e

    def _query(self, command: str) -> str:
        if not self.resource: raise LaserError("Instrument resource is not connected.")
        log.debug(f"QUERY: {command}")
        try:
            response = self.resource.query(command).strip()
            log.debug(f"RESPONSE: {response}")
            self._check_error(command)
            return response
        except pyvisa.VisaIOError as e:
            log.error(f"VISA Query Error on '{command}': {e}")
            raise LaserError(f"VISA Query Error: {e}") from e

    def _check_error(self, command: Optional[str] = None) -> None:
        try:
            err_str = self.resource.query(":SYST:ERR?").strip()
            if not err_str.startswith('+0,') and not err_str.startswith('0,'):
                self._last_error = err_str
                log.error(f"N7776C Error: {err_str} (triggered by command: {command})")
                match = re.match(r'^(-?\d+),"([^"]*)"', err_str)
                err_code = int(match.group(1)) if match else -1
                err_msg = match.group(2) if match else err_str
                raise LaserError(f"Instrument Error {err_code}: '{err_msg}'")
            else:
                self._last_error = None
        except pyvisa.VisaIOError as e:
            log.error(f"VISA Error during error check: {e}")
            raise LaserError(f"Failed to check instrument error status: {e}") from e

    def idn(self) -> str: return self._idn or "N/A"

    @property
    def laser_on(self) -> bool:
        state = self._query(":SOUR0:POW:STAT?")
        return state == '1'

    @laser_on.setter
    def laser_on(self, state: bool) -> None:
        cmd = ":SOUR0:POW:STAT 1" if state else ":SOUR0:POW:STAT 0"
        self._write(cmd)
        # Reduced logging verbosity for loops
        # log.info(f"Laser output set to {'ON' if state else 'OFF'}.")

    @property
    def power_unit(self) -> PowerUnit:
        unit_code = self._query(":SOUR0:POW:UNIT?")
        return PowerUnit.DBM if unit_code == '0' else PowerUnit.W

    @power_unit.setter
    def power_unit(self, unit: PowerUnit) -> None:
        if not isinstance(unit, PowerUnit): raise TypeError("unit must be a PowerUnit enum")
        unit_cmd = "DBM" if unit == PowerUnit.DBM else "W"
        self._write(f":SOUR0:POW:UNIT {unit_cmd}")
        log.info(f"Power unit set to {unit.value}.") # Log unit changes explicitly

    @property
    def power_dbm(self) -> float:
        if self.power_unit != PowerUnit.DBM: self.power_unit = PowerUnit.DBM
        power_val = self._query(":SOUR0:POW?")
        return float(power_val)

    @power_dbm.setter
    def power_dbm(self, dbm_value: float) -> None:
        if self.power_unit != PowerUnit.DBM: self.power_unit = PowerUnit.DBM
        self._write(f":SOUR0:POW {dbm_value:.4f}")
        # log.info(f"Power set to {dbm_value:.4f} dBm.") # Reduced logging

    @property
    def wavelength_nm(self) -> float:
        m_val = float(self._query(":SOUR0:WAV?"))
        return m_val * 1e9

    @wavelength_nm.setter
    def wavelength_nm(self, nm_value: float) -> None:
        self._write(f":SOUR0:WAV {nm_value:.4f}NM")
        # log.info(f"Wavelength set to {nm_value:.4f} nm.") # Reduced logging

    def setup_sweep(self, start_nm: float, stop_nm: float, speed_nm_s: float, step_nm: float = 0.1) -> None:
        log.debug(f"Config sweep: {start_nm}nm->{stop_nm}nm @{speed_nm_s}nm/s, step {step_nm}nm")
        self._write(":SOUR0:WAV:SWE:MODE CONT")
        self._write(f":SOUR0:WAV:SWE:STAR {start_nm:.4f}NM")
        self._write(f":SOUR0:WAV:SWE:STOP {stop_nm:.4f}NM")
        self._write(f":SOUR0:WAV:SWE:SPE {speed_nm_s:.4f}NM/S")
        self._write(f":SOUR0:WAV:SWE:STEP {step_nm:.4f}NM")

    def start_sweep(self) -> None:
        log.debug("Starting sweep...")
        self._write(":SOUR0:WAV:SWE STARt")

    def stop_sweep(self) -> None:
        log.debug("Stopping sweep...")
        self._write(":SOUR0:WAV:SWE STOP")

    def wait_for_sweep_completion(self, timeout_s: float = 60.0) -> None:
        log.debug("Waiting for sweep completion...")
        start_time = time.monotonic()
        while True:
            state = int(self._query(":SOUR0:WAV:SWE?"))
            if state == 0: log.debug("Sweep completed."); return
            if (time.monotonic() - start_time) > timeout_s:
                raise LaserError(f"Timeout waiting for sweep completion after {timeout_s}s")
            time.sleep(0.1) # Faster polling

    def enable_lambda_logging(self, enable: bool) -> None:
        state = 1 if enable else 0
        log.debug(f"{'Enabling' if enable else 'Disabling'} lambda logging.")
        self._write(f':SOUR0:WAV:SWE:LLOG {state}')

    def is_lambda_logging_enabled(self) -> bool:
        return self._query(':SOUR0:WAV:SWE:LLOG?') == '1'

    def get_lambda_log_points(self) -> int:
        return int(self._query(':SOUR0:READ:POIN? LLOG'))

    def get_lambda_log_data(self) -> List[float]:
        if not self.resource: raise LaserError("Instrument resource is not connected.")
        num_points = self.get_lambda_log_points()
        if num_points == 0: log.debug("No lambda log points available."); return []
        log.debug(f"Retrieving {num_points} lambda log points...")
        try:
            wavelengths_m = self.resource.query_binary_values(
                ':SOUR0:READ:DATA? LLOG', datatype='d', is_big_endian=False, container=list
            )
            if len(wavelengths_m) != num_points:
                 log.warning(f"Lambda log mismatch: Expected {num_points}, got {len(wavelengths_m)} points.")
            return [w * 1e9 for w in wavelengths_m]
        except pyvisa.errors.VisaIOError as e:
             log.error(f"VISA error reading binary lambda log: {e}")
             raise LaserError(f"Failed to read binary lambda log: {e}") from e
        except Exception as e:
             log.error(f"Error processing binary lambda log: {e}")
             raise LaserError(f"Error processing binary lambda log: {e}") from e

    def close(self) -> None:
        if self.resource:
            log.info(f"Closing connection to {self.resource_address}")
            try:
                # Ensure laser is off before closing in loops
                if self.laser_on: self.laser_on = False
                self.resource.close()
            except pyvisa.Error as e: log.warning(f"VISA error during close: {e}")
            finally: self.resource = None
        else: log.info("Connection already closed.")

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()
    def __repr__(self) -> str:
        conn_status = "Connected" if self.resource else "Closed"
        return f"<MinimalN777C(idn='{self._idn}', address='{self.resource_address}', status='{conn_status}')>"

# --- Function to run a single sweep and return data ---
def run_single_sweep(laser: N7776C, start_nm: float, stop_nm: float, speed_nm_s: float, step_nm: float) -> List[float]:
    """
    Sets up, runs a sweep with lambda logging, waits, and returns data.

    Args:
        laser: An initialized MinimalN777C object.
        start_nm: Sweep start wavelength in nm.
        stop_nm: Sweep stop wavelength in nm.
        speed_nm_s: Sweep speed in nm/s.
        step_nm: Step size for logging triggers in nm.

    Returns:
        A list of logged wavelengths in nm for this sweep, or empty list on failure.
    """
    try:
        laser.setup_sweep(start_nm=start_nm, stop_nm=stop_nm, speed_nm_s=speed_nm_s, step_nm=step_nm)
        laser.enable_lambda_logging(True)
        if not laser.is_lambda_logging_enabled():
             log.error("Failed to enable lambda logging.")
             return []

        estimated_time = abs(stop_nm - start_nm) / speed_nm_s
        wait_timeout = round(estimated_time) + 15 # Add buffer

        laser.start_sweep()
        laser.wait_for_sweep_completion(timeout_s=wait_timeout)
        logged_data = laser.get_lambda_log_data()
        # Disable logging after reading? Optional, but good practice
        laser.enable_lambda_logging(False)
        return logged_data
    except LaserError as e:
        log.error(f"Error during sweep: {e}")
        # Attempt to stop sweep if error occurs
        try:
            laser.stop_sweep()
        except Exception as stop_e:
            log.error(f"Failed to stop sweep after error: {stop_e}")
        return [] # Return empty list on error