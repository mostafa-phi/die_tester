import numpy as np
from typing import *
import plotly.graph_objects as go
from threading import Thread
from scipy.optimize import curve_fit
from scipy.stats import multivariate_normal
import itertools
import time
from tqdm import tqdm
from pprint import pprint

from src.DieTesterInstrument import SurugaSeikiDS102, DieTesterStage
from src.NIDAQPowermeter import PowermeterSystem

class FirstLightController:
    axis_convention = ['X', 'Y', 'Z']

    def __init__(self, pm: PowermeterSystem, die_tester_stage: DieTesterStage):
        """
        Controller for the first light search.
        """
        self.pgen = PathGenerator()
        self.flo = FirstLightOptimizer()
        self.pm = pm
        self.stg = die_tester_stage
    
    def unpackbits(self, x, num_bits):
        """Little-endian 1d uint array -> 2d array of bit arrays. Returns copy of the array with numbers replaced by bitstrings"""

        assert not np.issubdtype(x.dtype, np.floating), "Numpy data type must be int-like."

        xshape = list(x.shape)
        x = x.reshape([-1, 1])
        mask = 2**np.arange(num_bits, dtype=x.dtype).reshape([1, num_bits])
        return (x & mask).astype(bool).astype(int).reshape(xshape + [num_bits])
    
    def scan_path(self, stage, commands, speed_setting, line_numbers: int, **kwargs): # TODO
        """
        Scan a path given by a list of commands specifying relative coordinates. 
            stage: 'l' or 'r'.
            commands: Of the form (axis, distance), e.g. ('X', 10.0)
            speed_setting: speed setting of the device during travel
            line_numbers: line (or lines for XZ motion) on the DAQ port containing the device's motion output (0-32)
            kwargs:
                - perform_regression: Defaults to True. Whether to perform the gaussian regression and return the mean and cov.
                - samples_per_call: the number of samples captured before a motion callback. By default is a tenth of per second sample rate (0.1s callback).
                - return_to_origin: Defaults to True. Whether to return to the inital position where the scan was begun.
                - ls_params: Defaults to None. Initial parameters for gaussian least-squares regression, if necessary.
                - ls_kwargs: Defaults to None. Kwargs for the least squares regression, like 'method'.
                - minimum_move_time: Determined by the maximum rate that commands can be sent over usb. Defaults to the stage query delay. This is to prevent the code from querying the controller too fast (after short movements.)
                - timeout: Defaults to 3 seconds. Motion timeout in seconds for device to start motion.
                - round_commands: Defaults to True. Whether to round commands on the path to those taken exactly by the device (e.g. 4.077 microns -> 4.05 microns.)
                - figure_axes: Defaults to the axes in the commands (e.g. ['X', 'Y']) (if there's only one, selects the next one in the convention. e.g. 'Z' -> ['Z', 'X'])
        """
        ## Set Variables
        stage = stage.lower()
        assert stage == 'l' or stage == 'r', "Stage must be 'l' or 'r'."

        dev_xy, dev_z, _ = self.stg.allocation(stage)
        minimum_move_time = kwargs.get('minimum_move_time', max(dev_xy.query_delay, dev_z.query_delay))
        round_commands = kwargs.get('round_commands', True)
        if round_commands: # Round points to the pulses per micron of the driver
            driver_ppm = min(dev_xy.driver_ppm, dev_z.driver_ppm)
            commands = self.round_commands_to_device_ppm(commands, driver_ppm)
        
        return_to_origin = kwargs.get('return_to_origin', True)
        perform_regression = kwargs.get('perform_regression', True)
        samples_per_call = kwargs.get('samples_per_call', int(self.pm.sample_rate / 10) )
        timeout = kwargs.get('timeout', 3.0)
        ls_params = kwargs.get('ls_params', {})
        ls_kwargs = kwargs.get('ls_kwargs', {})

        axes = sorted(set([axis for axis, _ in commands]))
        if len(axes) == 1: # add axis if there's only one axis in the movement
            all_axes = self.axis_convention.copy()
            all_axes.remove(axes[0])
            axes.append(all_axes[0])
        figure_axes = kwargs.get('figure_axes', axes)

        # Save the current position
        origin = self.stg.query_position(stage)

        ## Set speed
        self.stg.set_speed(stage, speed_setting)

        ## Perform the scan
        full_pow_data = np.array([])
        full_mot_data = np.array([])

        pow_buffer = np.zeros(samples_per_call)
        mot_buffer = np.zeros(samples_per_call, dtype=np.uint32)

        # adding a line to specify the DAQ ai_channel to read from
        # self.pm.setup_power_task(ai_channel)

        print("Starting motion...")
        self.pm.start()
        try:
            with tqdm(total=len(commands), desc="Motion In Progress", unit="item") as pbar:
                for axis, d in commands:
                    # update progress bar
                    pbar.set_description(f"Current Move: ({axis}, {d})" )
                    pbar.update(1)
                    
                    # initialize variables
                    in_motion = False
                    motion_started = False  # set a second variable to check that motion started (for if the first callback is still not motion started.)
                    start_time = time.perf_counter()
                    waiting_for_minimum_move_time = True

                    # start collection and callback
                    self.stg.move_relative(stage, axis, d, wait=False)
                    while ( in_motion or not motion_started ) or waiting_for_minimum_move_time:
                        if time.perf_counter() - start_time > timeout:
                            if not motion_started:
                                raise Exception("Motion loop timed out without motion starting. Did your device move?")
                        
                        # read to buffer
                        self.pm.read(pow_buffer, mot_buffer, samples_per_call)
                        
                        # append data
                        mot_bitarray = np.bitwise_or.reduce(
                            self.unpackbits(mot_buffer, 32)[:, line_numbers],
                            axis=1,
                        )
                        full_pow_data = np.append(full_pow_data, pow_buffer)
                        full_mot_data = np.append(full_mot_data, mot_bitarray)

                        # update motion variable
                        in_motion = full_mot_data[-1]
                        if not motion_started:
                            motion_started = 1 in mot_bitarray
                        
                        waiting_for_minimum_move_time = time.perf_counter() - start_time < minimum_move_time

                ## final read (with no motion) for calibration and offset purposes
                # self.pm.read(pow_buffer, mot_buffer, samples_per_call)
                # mot_bitarray = self.unpackbits(mot_buffer, 32)[:, line_number]
                # full_pow_data = np.append(full_pow_data, pow_buffer)
                # full_mot_data = np.append(full_mot_data, mot_bitarray)
    
        except Exception as e:
            print(f"Scan failed with exception: {e}.")
            raise e
        finally:
            self.pm.stop()

        ## Return to inital position if specified.
        if return_to_origin:
            print("Returning to original position...")
            self.stg.move_absolute(
                stage,
                x=origin[0],
                y=origin[1],
                z=origin[2],
            )

        ## Attach point coordinates to power data.
        _, power_groups = self.motion_groups(full_pow_data, full_mot_data)

        def command_to_datapoint_delta(cmd, axes):
            if cmd[0] == axes[0]:
                return (cmd[1], 0)
            elif cmd[0] == axes[1]:
                return (0, cmd[1])
            else:
                raise ValueError("Attempted to convert malformed command to coordinates. Check this function.")

        datapoints = None
        for i in range(0, len(power_groups)): # encode positions to power groups using the respective paths
            
            if i == 0: 
                startpoint = [0, 0] # starting position is considered (0, 0)
                endpoint = command_to_datapoint_delta(commands[i], figure_axes)
            else: 
                startpoint = (
                    endpoint[0],
                    endpoint[1],
                )
                delta = command_to_datapoint_delta(commands[i], figure_axes)
                endpoint = (
                    endpoint[0] + delta[0],
                    endpoint[1] + delta[1],
                )

            pow_data_chunk = np.asarray(power_groups[i]).reshape(-1, 1)
            pos = np.asarray(
                self.encode_position(
                    pow_data_chunk.shape[0],
                    startpoint,
                    endpoint,
                )
            )

            if datapoints is None:
                datapoints = np.concat((pos, pow_data_chunk), axis=1)
            else:
                datapoints = np.append(
                    datapoints,
                    np.concat((pos, pow_data_chunk), axis=1),
                    axis=0,
                )

        ## Prepare data for being returned
        return_data = {
                'datapoints': datapoints,
                'raw_data': (full_pow_data, full_mot_data),
                'origin': origin,
            }
        
        if perform_regression:  # If doing gaussian regression
            print("Fitting gaussian regression to datapoints...")

            popt = self.flo.multivariate_normal_regression(datapoints, ls_params, ls_kwargs=ls_kwargs)

            scale = popt['scale']
            mean = popt['mean']
            cov = popt['cov']

            print(f"Found optimal parameters.")
            print(f"Mean: {mean}")
            print(f"Cov: {cov}")


            xaxis_title = f'{figure_axes[0]} (μm)'
            yaxis_title = f'{figure_axes[1]} (μm)'

            return_data.update({
                'mean': mean,
                'cov': cov,
                'u_mean': [
                    np.sqrt(popt['param_cov'][1,1]),
                    np.sqrt(popt['param_cov'][2,2]),
                ], # mean uncertainty 
                'figure': self.visualize_normal_regression(datapoints, popt, xaxis_title=xaxis_title, yaxis_title=yaxis_title),
            })

            return return_data
        else: 
            xaxis_title = f'{figure_axes[0]} (μm)'
            yaxis_title = f'{figure_axes[1]} (μm)'
            return_data.update({
                "figure": self.visualize_points(datapoints, xaxis_title=xaxis_title, yaxis_title=yaxis_title)
            })

            return return_data
    def visualize_points(self, datapoints, xaxis_title='Axis1', yaxis_title='Axis2', zaxis_title='Radiant Power (Voltage)'):
        fig = go.Figure()
        scatter = go.Scatter3d(
            x=datapoints[:, 0],
            y=datapoints[:, 1],
            z=datapoints[:, 2],
            mode='markers',
            marker=dict(
                size=2,
                color=datapoints[:, 2],
                colorscale='Viridis',
                opacity = 0.8,
            ),
            name='Datapoints'
        )
        fig.add_trace(scatter)
        fig.update_layout(
            width=500,
            height=500,
            autosize=True,
            title_text = "First Light Visualization",
            scene=dict(
                aspectmode='cube',
                xaxis_title=xaxis_title,
                yaxis_title=yaxis_title,
                zaxis_title=zaxis_title
            )
        )
        fig.update_yaxes(  # Give X and Y axis the same scale.
            scaleanchor="x",
            scaleratio=1,
        )

        return fig

    def visualize_normal_regression(self, datapoints, params, **kwargs):
        scale = params['scale']
        mean = params['mean']
        cov = params['cov']

        xmin = np.min(datapoints[:, 0])
        xmax = np.max(datapoints[:, 0])
        ymin = np.min(datapoints[:, 1])
        ymax = np.max(datapoints[:, 1])

        x = np.linspace(xmin, xmax, 100)
        y = np.linspace(ymin, ymax, 100)
        X, Y = np.meshgrid(x, y)
        pos = np.dstack((X, Y))

        rv = multivariate_normal(mean=mean, cov=cov, allow_singular=True)
        Z = scale * rv.pdf(pos)

        fig = self.visualize_points(datapoints, **kwargs)    
        fig.add_trace(go.Surface(x=X, y=Y, z=Z))
        return fig
            
    def motion_groups(self, pow_data, mot_data):
        group0 = []
        group1 = []
        for k, g in itertools.groupby(zip(mot_data, pow_data), key=lambda x: x[0]):
            if k==0:
                group0.append([x for _,x in g])
            elif k==1:
                group1.append([x for _,x in g])
            else:
                raise ValueError("Expected binary motion data.")
        
        return group0, group1

    
    def encode_position(self, num_points, startpoint, endpoint, include_startpoint=True, include_endpoint=True):
        """
        Extrapolate data measurements from time-based continuous motion into positional data.
            start_pos: (x, y)
            end_pos: (x, y)
            include_startpoint: True by default
            include_endpoint: True by default
        """
        if include_startpoint:
            start_offset = 0
        else:
            start_offset = 1
        
        if include_endpoint:
            end_offset = 0
        else:
            end_offset = 1
        
    
        posdata = []
        deltax = endpoint[0] - startpoint[0]
        deltay = endpoint[1] - startpoint[1]

        num_steps = num_points - 1 + start_offset + end_offset
        stepfrac = 1 / num_steps
        
        for i in range(start_offset, (num_steps + 1) - end_offset):
            posdata.append((
                startpoint[0] + stepfrac * i * deltax,
                startpoint[1] + stepfrac * i * deltay,
            ))
        
        return posdata

        
    def round_commands_to_device_ppm(self, commands, pulses_per_micron):
        """Rounds path commands to the nearest device step in such a way that the travels correspond to the actual movement of the device. (as encoded in DieTesterInstrument)"""
        rounded_commands = [
            (axis, np.round(pulses_per_micron * d) / pulses_per_micron) for axis, d in commands
        ]
        return rounded_commands
    
class FirstLightOptimizer:
    def multivariate_normal_regression(self, points, initial_params, ls_kwargs={}):
        """
        Multivariate normal regression on a set of points.

        initial_params:
            scale: Vertical scale of the distribution, because power is proportional to the gaussian. default 1.0.
            mean_x: X component of the mean. default computed as the mean of x coordinates.
            mean_y: Y component of the mean. default computed as the mean of y coordinates.
            cov: covariance matrix. default computed as the covariance of the data.
            param_cov: covariance for the fitted parameters.
        ls_kwargs: kwargs for the least squares fit.
        """
        
        def mvn(coords, scale, mean_x, mean_y, l11, l21, l22):
            
            L = np.array([[l11, 0], [l21, l22]])
            cov_matrix = L @ L.T  # Positive semidefinite covariance matrix        
            mean_vector = np.array([mean_x, mean_y])
            
            Z = scale * multivariate_normal.pdf(coords, mean=mean_vector, cov=cov_matrix, allow_singular=True)

            # Apply the scale factor to the log likelihood
            return Z
        
        x = points[:, 0]
        y = points[:, 1]

        initial_scale = initial_params.get('scale', 1.0)
        initial_mean_x = initial_params.get('mean_x', np.mean(x))
        initial_mean_y = initial_params.get('mean_y', np.mean(y))
        initial_cov = initial_params.get('cov', np.cov(x, y))
        initial_l11 = np.sqrt(initial_cov[0, 0])
        initial_l21 = initial_cov[1, 0] / initial_l11
        initial_l22 = np.sqrt(initial_cov[1, 1] - initial_l21**2)

        initial_guess = [initial_scale, initial_mean_x, initial_mean_y, initial_l11, initial_l21, initial_l22]
        bounds = ([0, -np.inf, -np.inf, 0, -np.inf, 0], np.inf)
        try:
            popt, pcov = curve_fit(mvn, points[:, :2], points[:, 2], p0=initial_guess, bounds=bounds, **ls_kwargs)
        except Exception as e:
            print(f'ERROR - Gaussian regression failed with error message: {e}')
            popt = initial_guess
            pcov = np.zeros((6,6))

        optimal_scale = popt[0]
        optimal_mean = popt[1:3]
        L_optimal = np.array([[popt[3], 0], [popt[4], popt[5]]])
        optimal_covariance = L_optimal @ L_optimal.T

        return {
            'scale': optimal_scale, # account for normalization.
            'mean': optimal_mean,
            'cov': optimal_covariance,
            'param_cov': pcov
        }

class PathGenerator:
    def generate_linear_spiral(self, scan_dim, num_steps: int, axis1='X', axis2='Y') -> List[Tuple[str, int]]:
        """
        returns a list of coordinates for a linear spiral first light path. (CCW)
            scan_dim: (width, height)
            axis1: axis for the 'width' setting
            axis2: axis for the 'height' setting
        """

        step_width = scan_dim[0] / num_steps
        step_height = scan_dim[1] / num_steps

        commands = []
        directions = [(axis1, 1), (axis2, 1), (axis1, -1), (axis2, -1)] # CCW: right, up, left, down

        dir_idx = 0 # index of direction, start with 0 -> left
        for ring in range(1, num_steps + 1): 
            # one 'L-shaped step'
            for _ in range(2):
                axis, dir = directions[dir_idx % 4]
                
                if axis == axis1: 
                    commands.append(
                        (axis, dir * (ring * step_width),)
                    )
                elif axis == axis2:
                    commands.append(
                        (axis, dir * (ring * step_height),)
                    )
                
                dir_idx += 1

        return commands
    
    def generate_rectangle(self, scan_dim, axis1='X', axis2='Y') -> List[Tuple[str, int]]:
        """
        generates a rectangle of the specified width and height dimensions.
            scan_dim: (width, height)
        """

        xdelta = scan_dim[0] / 2
        ydelta = scan_dim[1] / 2
        commands = [
            (axis1, - xdelta),
            (axis2, - ydelta),
            (axis1, + 2 * xdelta),
            (axis2, + 2 * ydelta),
            (axis1, - 2 * xdelta),
            (axis2, - 2 * ydelta),
        ]

        return commands
    

