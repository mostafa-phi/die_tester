import time
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import nidaqmx
from nidaqmx.constants import Edge

from src.NIDAQPowermeter import PowermeterSystem
from src.FirstLightController import FirstLightController


class WaveguideAlignmentController:
    """
    Auto-alignment and full-chip-stepping logic for the die tester.

    This class collects everything that used to be a loose function (or a copy-pasted
    block) inside main_v4.ipynb: power-unit conversions, the raster/Z-scan first-light
    routines, the optical-switch routing helper, the transfer-function measurement, and
    the per-waveguide / all-waveguide alignment loops. The notebook should only need to
    instantiate this class once and then call its methods.

    Typical use:
        aligner = WaveguideAlignmentController(stg, switch, inp_pow=inp_pow)

        # single waveguide, interactively:
        result = aligner.align_waveguide(device_no, z_trans_l, z_trans_r)

        # step through the whole chip:
        aligner.run_all_waveguides(
            first_device_no=2, last_device_no=66,
            file_path=file_path, z_trans_l=2, z_trans_r=2,
            tsl770=TSL770, daq_factory=USB6363, folder_path=folder_path,
        )
    """

    # CSV header used for the saved transfer-function data files.
    header = r'Tapvolt770(V),SHGvoltage(V),Trigger volt(V), Wavelength(um)'

    def __init__(self, stg, switch, device_name='Dev1', sample_rate=5e3, inp_pow=None):
        """
        stg: DieTesterStage instance.
        switch: pyvisa optical-switch resource (already opened/connected).
        device_name: NI DAQ device name used for the powermeter tasks.
        sample_rate: sample rate (Hz) used for the powermeter tasks.
        inp_pow: input power (mW) after the lensed fiber, used for insertion-loss calc.
                 Can also be set later via `aligner.inp_pow = ...`.
        """
        self.stg = stg
        self.switch = switch
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.inp_pow = inp_pow

        # Populated by set_channel(); the powermeter task has to be rebuilt whenever
        # the analog input channel changes (matches the original notebook behavior).
        self.pm = None
        self.flc = None
        self.ai_channel = None

    # ------------------------------------------------------------------
    # Switch / channel setup
    # ------------------------------------------------------------------
    def switch_route(self, route_no, output_port):
        """Route the optical switch, e.g. switch_route('1', '1')."""
        self.switch.write('rout' + route_no + ':chan1 A,' + output_port)

    def set_channel(self, ai_channel):
        """
        (Re)build the PowermeterSystem + FirstLightController on a given DAQ analog
        input channel. Closes the previous powermeter task first, if any, so tasks
        don't pile up on the device as the channel is switched between scans.
        """
        if self.pm is not None:
            try:
                self.pm.close()
            except Exception:
                pass
        self.pm = PowermeterSystem(self.device_name, self.sample_rate, ai_channel)
        self.flc = FirstLightController(self.pm, self.stg)
        self.ai_channel = ai_channel
        return self.pm, self.flc

    # ------------------------------------------------------------------
    # Power-unit conversions
    # ------------------------------------------------------------------
    @staticmethod
    def pd_to_pow(x, g):
        """Convert NewFocus PD tap output voltage `x` (at gain setting `g`) to power in mW."""
        R = 0.55  # responsivity, can interpolate the graph for more accurate values
        return x / (g * R)

    @staticmethod
    def log_pd_to_pow(Vout):
        """Convert a log-detector output voltage to power in mW."""
        Vy = 0.3
        Iz = 100e-12
        Ipd = Iz * 10 ** (Vout / Vy)
        R = 0.9
        return (Ipd / R) * 1e3

    # ------------------------------------------------------------------
    # Curve fitting
    # ------------------------------------------------------------------
    @staticmethod
    def gaussian_fit_func(xy, a, x0, sigxsq, y0, sigysq):
        x = xy[:, 0]
        y = xy[:, 1]
        return a * np.exp(-((x - x0) ** 2 / sigxsq + (y - y0) ** 2 / sigysq))

    def raster_fit(self, datapoints):
        """Fit a 2D gaussian to a raster scan's datapoints and return (x0, y0) of the peak."""
        xy_points = datapoints[:, 0:2]
        P_points = datapoints[:, 2]

        p0 = [
            1,
            0, (xy_points[:, 0].max() - xy_points[:, 0].min()) / 2,
            0, (xy_points[:, 1].max() - xy_points[:, 1].min()) / 2,
        ]

        fitparams, fitcov = curve_fit(self.gaussian_fit_func, xy_points, P_points, p0, maxfev=5000)

        x0 = fitparams[1]
        y0 = fitparams[3]

        if np.abs(x0) > 3.5 or np.abs(y0) > 7:  # safety check in case the fit is unreasonable
            x0 = y0 = 0

        print(f"Moved to {[x0, y0]}")
        print('Max is: ', np.max(P_points))
        return x0, y0

    @staticmethod
    def parabola(x, a, b, c):
        return a * x + b * x ** 2 + c

    # ------------------------------------------------------------------
    # Scans
    # ------------------------------------------------------------------
    def raster_scan(self, stage, broad_range):
        """
        Perform an XY raster (linear spiral) scan on 'l' or 'r' and return the
        (X, Y, power) datapoints.
        """
        line_numbers = [0, 1, 2]  # motion i/o for left XY, right XY, all Z
        speed = 9
        if broad_range:
            commands = self.flc.pgen.generate_linear_spiral((20, 20), 40)
        else:
            commands = self.flc.pgen.generate_linear_spiral((5, 5), 10)
        result = self.flc.scan_path(stage, commands, speed, line_numbers, perform_regression=False)
        return result['datapoints']

    def z_scan(self, stage, broad_range):
        """Perform a Z scan on 'l' or 'r', fit a parabola, and return the optimal Z offset."""
        if broad_range:
            commands = [['Z', 1], ['Z', -5]]
        else:
            commands = [['Z', 1], ['Z', -2]]

        line_numbers = [0, 1, 2]
        speed = 6

        result = self.flc.scan_path(stage, commands, speed, line_numbers, perform_regression=False)
        datapoints = result['datapoints']
        z_tun = datapoints[:, 0]
        Pz_tun = datapoints[:, 2]

        fitparams, fitcov = curve_fit(self.parabola, z_tun, Pz_tun)
        fit_par = self.parabola(z_tun, *fitparams)
        z_opt = z_tun[np.argmax(fit_par)]
        print(z_opt)
        return z_opt

    def fine_tune(self):
        """
        Full fine-alignment sequence (broad Z-scan + narrow XY raster) for both fibers.
        NOTE: preserved verbatim from the original notebook, which moved the 'l' stage
        along Z for both the left AND right z-translation results. Verify this is
        intentional before relying on it -- it may be a pre-existing bug (likely meant
        `self.stg.move_relative('r', 'Z', z_trans_r)`).
        """
        z_trans_l = self.z_scan('l', True)
        self.stg.move_relative('l', 'Z', z_trans_l)
        raster_data = self.raster_scan('l', False)
        x0, y0 = self.raster_fit(raster_data)
        self.stg.move_relative('l', 'X', x0)
        self.stg.move_relative('l', 'Y', y0)

        z_trans_r = self.z_scan('r', True)
        self.stg.move_relative('l', 'Z', z_trans_r)  # see docstring note above
        raster_data = self.raster_scan('r', False)
        x0, y0 = self.raster_fit(raster_data)
        self.stg.move_relative('r', 'X', x0)
        self.stg.move_relative('r', 'Y', y0)

        return raster_data, z_trans_l, z_trans_r

    # ------------------------------------------------------------------
    # Chip stepping
    # ------------------------------------------------------------------
    def prep_next_waveguide(self, device_no):
        """
        Advance the chip stage to the next waveguide position without performing an
        alignment (used when the current waveguide didn't have enough signal to align to).
        Returns (device_no, il) with il = -100 as a sentinel "no signal" insertion loss.
        """
        il = -100
        self.stg.set_speed('m', 9)
        if device_no % 2 == 0:
            self.stg.move_relative('m', 'X', -(254 - 8), wait=True)
        else:
            self.stg.move_relative('m', 'X', -8, wait=True)
        return device_no, il

    def advance_chip(self, device_no):
        """Move the chip stage to the next waveguide (successful-alignment path)."""
        self.stg.set_speed('m', 9)
        if device_no % 2 == 0:
            self.stg.move_relative('m', 'X', -(254 - 8), wait=True)
        else:
            self.stg.move_relative('m', 'X', -8, wait=True)

    # ------------------------------------------------------------------
    # Transfer function measurement
    # ------------------------------------------------------------------
    def measure_transfer_function(self, tsl770, daq, folder_path, device_no):
        """
        Sweep the tunable laser (TSL770) and record the transfer function on the DAQ,
        saving a plot (device_no_<n>.png) and raw data (device_no_<n>.csv) to folder_path.

        tsl770: connected SantecTunableLaser.TSL instance.
        daq: a USB6363-like object with an `ai_task` (nidaqmx.Task) already configured
             with the desired analog input channels, plus configure_sampling/start/read/stop.
        """
        start_wavelength = 1500e-9
        stop_wavelength = 1620e-9
        sample_rate = 10000
        sweep_speed = 200  # nm/s
        sweep_range = stop_wavelength - start_wavelength
        sweep_time = sweep_range * 1e9 / sweep_speed  # seconds
        n770 = int(sweep_time * sample_rate)
        samples = np.arange(n770)

        trigger_step = 100e-12

        # Configure TSL770 for sweeping
        tsl770.wavelength_start(start_wavelength)
        tsl770.wavelength_stop(stop_wavelength)
        tsl770.trigger_step(trigger_step)  # useful for 200 nm/s; caps sweep speed, set first
        tsl770.sweep_speed(sweep_speed)
        tsl770.trigger_setting(1)  # 1 - time trigger; nonuniform wvl spacing, 0 - wavelength trigger
        tsl770.sweep_mode(1)  # continuous sweep

        # Configure DAQ
        daq.ai_task.triggers.start_trigger.cfg_dig_edge_start_trig(
            trigger_source="/Dev2/PFI5", trigger_edge=Edge.RISING
        )

        t_samp_daq = 1 / sample_rate
        t_samp_770 = trigger_step * 1e9 / sweep_speed
        daq.configure_sampling(sample_rate, n770)
        tsl770.wavelength(start_wavelength)

        time.sleep(0.6)  # allow lasers to settle

        # Measure data
        tsl770.sweep_state(1)
        daq.start()
        data = daq.read()
        daq.stop()

        raw_wavelength_data = tsl770.read_wavelength()
        t_daq = t_samp_daq * samples
        t_770 = t_samp_770 * np.arange(len(raw_wavelength_data))
        steps_770 = np.interp(t_daq, t_770, raw_wavelength_data)

        time.sleep(0.6)

        folder_name = folder_path + '/device_no_'

        plt.clf()
        plt.plot(steps_770, np.array(data[0][1]))
        plt.xlabel(r'Wavelength ($\mu$m)')
        plt.ylabel('PD output voltage (V)')
        plt.savefig(folder_name + str(device_no) + '.png')

        dataT = np.reshape(data, (3, len(steps_770))).T
        data_new = np.column_stack((dataT, steps_770))
        np.savetxt(folder_name + str(device_no) + '.csv', data_new, delimiter=',', header=self.header)

    # ------------------------------------------------------------------
    # Per-waveguide auto-alignment
    # ------------------------------------------------------------------
    def align_waveguide(self, device_no, z_trans_l, z_trans_r, threshold=0.02):
        """
        Full auto-alignment sequence for a single waveguide:
          1. Broad raster scan on 'r' fiber (femto detector). Bail out (and advance the
             chip) if the peak is below `threshold`.
          2. Broad raster scan on 'l' fiber.
          3. Narrow Z-scan (x2) + XY raster scan on 'l' fiber (log detector).
          4. Narrow Z-scan (x2) + XY raster scan on 'r' fiber (log detector).
          5. Compute insertion loss from the peak of the final raster.

        Returns a dict: {device_no, il, z_trans_l, z_trans_r, aligned}.
        `aligned` is False if the sequence bailed out early (no/insufficient signal, or a
        fit failure) -- in that case the chip has already been advanced to the next
        waveguide via prep_next_waveguide, so the caller should NOT advance it again.
        """
        # --- Broad scan, femto detector ---
        self.switch_route('1', '1')
        self.set_channel('ai0')

        stage = 'r'
        raster_data = self.raster_scan(stage, True)
        if np.max(raster_data[:, 2]) < threshold:
            device_no, il = self.prep_next_waveguide(device_no)
            return {'device_no': device_no, 'il': il, 'z_trans_l': z_trans_l,
                    'z_trans_r': z_trans_r, 'aligned': False}
        x0, y0 = self.raster_fit(raster_data)
        self.stg.move_relative(stage, 'X', x0, wait=True)
        self.stg.move_relative(stage, 'Y', y0, wait=True)

        stage = 'l'
        raster_data = self.raster_scan(stage, True)
        try:
            x0, y0 = self.raster_fit(raster_data)
        except RuntimeError as e:
            print(f"Waveguide {device_no} failed to fit: {e}")
            device_no, il = self.prep_next_waveguide(device_no)
            return {'device_no': device_no, 'il': il, 'z_trans_l': z_trans_l,
                    'z_trans_r': z_trans_r, 'aligned': False}
        self.stg.move_relative(stage, 'X', x0, wait=True)
        self.stg.move_relative(stage, 'Y', y0, wait=True)

        # --- Small scan, log detector ---
        self.switch_route('1', '2')
        self.set_channel('ai1')

        for stage in ('l', 'r'):
            # Z-scan run twice per fiber, matching the original loop.
            for _ in range(2):
                z_trans = self.z_scan(stage, True)
                self.stg.move_relative(stage, 'Z', z_trans)
                if stage == 'l':
                    z_trans_l = z_trans
                else:
                    z_trans_r = z_trans

            raster_data = self.raster_scan(stage, False)
            try:
                x0, y0 = self.raster_fit(raster_data)
            except RuntimeError as e:
                print(f"Waveguide {device_no} failed to fit: {e}")
                device_no, il = self.prep_next_waveguide(device_no)
                return {'device_no': device_no, 'il': il, 'z_trans_l': z_trans_l,
                        'z_trans_r': z_trans_r, 'aligned': False}
            self.stg.move_relative(stage, 'X', x0)
            self.stg.move_relative(stage, 'Y', y0)

        if self.inp_pow is None:
            raise ValueError("`inp_pow` must be set on the controller before computing insertion loss.")

        il = 10 * np.log10(self.log_pd_to_pow(np.max(raster_data[:, 2])) / self.inp_pow)
        return {'device_no': device_no, 'il': il, 'z_trans_l': z_trans_l,
                'z_trans_r': z_trans_r, 'aligned': True}

    # ------------------------------------------------------------------
    # All-waveguide loop
    # ------------------------------------------------------------------
    def run_all_waveguides(self, first_device_no, last_device_no, file_path,
                            z_trans_l=2, z_trans_r=2, threshold=0.02,
                            measure_transfer_function=True,
                            tsl770=None, daq_factory=None, folder_path=None,
                            wavelength=1560e-9):
        """
        Step through every waveguide from first_device_no to last_device_no (inclusive):
        auto-align (align_waveguide), append insertion loss to file_path (CSV), optionally
        measure + save a transfer function, then advance the chip to the next waveguide.

            file_path: CSV path to append rows [device_no, il] to (header assumed already written).
            measure_transfer_function: if True, requires tsl770, daq_factory, and folder_path.
            tsl770: connected SantecTunableLaser.TSL instance.
            daq_factory: zero-arg callable returning a fresh DAQ object (e.g. `USB6363`),
                         used once per successfully-aligned waveguide.
            wavelength: laser wavelength (m) to return to after each transfer-function sweep.
        """
        if measure_transfer_function and (tsl770 is None or daq_factory is None or folder_path is None):
            raise ValueError("tsl770, daq_factory, and folder_path are required when "
                              "measure_transfer_function=True.")

        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            for device_no in range(first_device_no, last_device_no + 1):
                result = self.align_waveguide(device_no, z_trans_l, z_trans_r, threshold=threshold)
                device_no = result['device_no']
                il = result['il']
                z_trans_l = result['z_trans_l']
                z_trans_r = result['z_trans_r']

                writer.writerow([device_no, il])
                f.flush()
                print(f"{device_no}, Insertion loss- {il}")

                if not result['aligned']:
                    # Chip was already advanced inside prep_next_waveguide().
                    continue

                if measure_transfer_function:
                    self.switch_route('1', '3')
                    time.sleep(0.1)  # time for the switch
                    daq = daq_factory()
                    daq.ai_task = nidaqmx.Task()
                    daq.ai_task.ai_channels.add_ai_voltage_chan("Dev2/ai5, Dev2/ai4, Dev2/ai0")

                    self.measure_transfer_function(tsl770, daq, folder_path, device_no)

                    daq.close()
                    tsl770.wavelength(wavelength)
                    time.sleep(0.5)

                self.advance_chip(device_no)

        return z_trans_l, z_trans_r
