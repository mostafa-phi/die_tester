import threading
import numpy as np
import plotly.graph_objects as go
import ipywidgets as widgets
from IPython.display import display


class ScanControlGUI:
    """
    Interactive raster-scan / Z-scan panel: raster scan controls + plot on the left,
    Z-scan controls + plot on the right.

    Each side: pick stage ('l' or 'r') and range (broad/narrow), click Run. Once a scan
    finishes, the interactive plot renders below its controls with the fit marked --
    the gaussian center for the raster scan, the parabola maximum for the Z scan -- and
    a separate "Move to ..." button lights up to actually move the stage there.

    Requires the switch route + DAQ channel to already be set for the detector you want
    to scan on (same as the manual scan cells elsewhere in the notebook), e.g.:
        aligner.switch_route('1', '1'); aligner.set_channel('ai0')   # broad, femto detector
        aligner.switch_route('1', '2'); aligner.set_channel('ai1')   # narrow, log detector

    Usage:
        scan_gui = ScanControlGUI(aligner)
        scan_gui.display()
    """

    def __init__(self, aligner):
        self.aligner = aligner
        self.stg = aligner.stg
        # Serializes scans/moves -- the 'l'/'r' stages share a Z-axis device, and only one
        # scan or move should be in flight on the powermeter/stage hardware at a time.
        self._move_lock = threading.Lock()
        self._run_buttons = []
        self.status_label = widgets.Label(value="Ready.")

        self._raster_result = None  # {'stage': .., 'x0': .., 'y0': ..}
        self._z_result = None       # {'stage': .., 'z_opt': ..}

    # ------------------------------------------------------------------
    def display(self):
        """
        Build and display the panel. Does not return the widget (see StageControlGUI for
        why: returning it causes Jupyter to auto-display it a second time).
        """
        raster_controls, raster_output = self._build_raster_panel()
        z_controls, z_output = self._build_z_panel()

        layout = widgets.VBox([
            widgets.HBox([raster_controls, z_controls]),
            widgets.HBox([raster_output, z_output]),
            self.status_label,
        ])
        display(layout)

    # ------------------------------------------------------------------
    # Panel construction
    # ------------------------------------------------------------------
    def _build_raster_panel(self):
        title = widgets.HTML("<b>Raster Scan (XY)</b>")
        stage_toggle = widgets.ToggleButtons(
            options=[('Left (l)', 'l'), ('Right (r)', 'r')], description='Stage:',
        )
        range_toggle = widgets.ToggleButtons(
            options=[('Broad', True), ('Narrow', False)], description='Range:',
        )
        run_button = widgets.Button(description="Run Raster Scan", button_style='primary')
        move_button = widgets.Button(
            description="Move to Gaussian Center", button_style='success', disabled=True,
        )
        result_label = widgets.Label(value="No scan yet.")
        output = widgets.Output(layout=widgets.Layout(border='1px solid lightgray', width='480px'))

        run_button.on_click(
            lambda b: self._on_run_raster(stage_toggle, range_toggle, move_button, result_label, output)
        )
        move_button.on_click(lambda b: self._on_move_raster(result_label))

        self._run_buttons.append(run_button)

        controls = widgets.VBox([
            title, stage_toggle, range_toggle,
            widgets.HBox([run_button, move_button]),
            result_label,
        ], layout=widgets.Layout(border='1px solid gray', padding='6px', margin='4px', width='480px'))

        return controls, output

    def _build_z_panel(self):
        title = widgets.HTML("<b>Z Scan</b>")
        stage_toggle = widgets.ToggleButtons(
            options=[('Left (l)', 'l'), ('Right (r)', 'r')], description='Stage:',
        )
        range_toggle = widgets.ToggleButtons(
            options=[('Broad', True), ('Narrow', False)], description='Range:',
        )
        run_button = widgets.Button(description="Run Z Scan", button_style='primary')
        move_button = widgets.Button(
            description="Move to Maxima", button_style='success', disabled=True,
        )
        result_label = widgets.Label(value="No scan yet.")
        output = widgets.Output(layout=widgets.Layout(border='1px solid lightgray', width='480px'))

        run_button.on_click(
            lambda b: self._on_run_zscan(stage_toggle, range_toggle, move_button, result_label, output)
        )
        move_button.on_click(lambda b: self._on_move_zscan(result_label))

        self._run_buttons.append(run_button)

        controls = widgets.VBox([
            title, stage_toggle, range_toggle,
            widgets.HBox([run_button, move_button]),
            result_label,
        ], layout=widgets.Layout(border='1px solid gray', padding='6px', margin='4px', width='480px'))

        return controls, output

    # ------------------------------------------------------------------
    # Move/scan execution (threaded + serialized)
    # ------------------------------------------------------------------
    def _set_run_buttons_enabled(self, enabled):
        for b in self._run_buttons:
            b.disabled = not enabled

    def _run_async(self, description, fn):
        """
        Run a scan/move. Runs synchronously on the calling (kernel) thread -- NOT on a
        background thread. A scan builds a plotly figure and displays it inside an
        ipywidgets.Output(); that capture relies on IPython's display machinery, which is
        not reliably thread-safe, so building/displaying the figure from a background
        thread leaves the plot silently missing from the panel. Blocking the kernel while
        a scan runs matches how the rest of this codebase already works (scan_path, move_relative,
        etc. all block synchronously too).
        """
        if not self._move_lock.acquire(blocking=False):
            self.status_label.value = "Busy - a scan/move is already in progress. Please wait."
            return

        self._set_run_buttons_enabled(False)
        self.status_label.value = f"Running: {description} ..."

        try:
            fn()
            self.status_label.value = f"Done: {description}."
        except Exception as e:
            self.status_label.value = f"ERROR during {description}: {e}"
        finally:
            self._move_lock.release()
            self._set_run_buttons_enabled(True)

    def _check_flc_ready(self):
        if self.aligner.flc is None:
            raise RuntimeError(
                "No DAQ channel/route selected yet. Call aligner.switch_route(...) and "
                "aligner.set_channel(...) first (same as the manual scan cells)."
            )

    # ------------------------------------------------------------------
    # Raster scan callbacks
    # ------------------------------------------------------------------
    def _on_run_raster(self, stage_toggle, range_toggle, move_button, result_label, output):
        stage = stage_toggle.value
        broad = range_toggle.value

        def fn():
            self._check_flc_ready()
            datapoints = self.aligner.raster_scan(stage, broad)
            x0, y0 = self.aligner.raster_fit(datapoints)

            peak_idx = np.argmax(datapoints[:, 2])
            peak_z = datapoints[peak_idx, 2]

            fig = self.aligner.flc.visualize_points(
                datapoints, xaxis_title='X (\u03bcm)', yaxis_title='Y (\u03bcm)',
            )
            fig.add_trace(go.Scatter3d(
                x=[x0], y=[y0], z=[peak_z],
                mode='markers',
                marker=dict(size=8, color='red', symbol='diamond'),
                name='Gaussian center',
            ))
            fig.update_layout(title_text=f"Raster Scan - stage '{stage}'")

            self._raster_result = {'stage': stage, 'x0': x0, 'y0': y0}

            with output:
                output.clear_output(wait=True)
                print(f"Gaussian fit center (stage '{stage}'): X = {x0:.3f} \u03bcm, Y = {y0:.3f} \u03bcm")
                fig.show()

            result_label.value = f"Center: X={x0:.3f} \u03bcm, Y={y0:.3f} \u03bcm"
            move_button.disabled = False

        self._run_async(f"raster scan '{stage}'", fn)

    def _on_move_raster(self, result_label):
        if self._raster_result is None:
            return
        stage = self._raster_result['stage']
        x0 = self._raster_result['x0']
        y0 = self._raster_result['y0']

        def fn():
            self.stg.move_relative(stage, 'X', x0, wait=True)
            self.stg.move_relative(stage, 'Y', y0, wait=True)
            result_label.value = f"Moved '{stage}' to X={x0:.3f}, Y={y0:.3f} \u03bcm"

        self._run_async(f"move '{stage}' to gaussian center", fn)

    # ------------------------------------------------------------------
    # Z scan callbacks
    # ------------------------------------------------------------------
    def _on_run_zscan(self, stage_toggle, range_toggle, move_button, result_label, output):
        stage = stage_toggle.value
        broad = range_toggle.value

        def fn():
            self._check_flc_ready()
            result = self.aligner.z_scan_verbose(stage, broad)
            z_tun = result['z_tun']
            Pz_tun = result['Pz_tun']
            fitparams = result['fitparams']
            z_opt = result['z_opt']

            z_fit_curve = np.linspace(np.min(z_tun), np.max(z_tun), 200)
            P_fit_curve = self.aligner.parabola(z_fit_curve, *fitparams)
            P_at_opt = self.aligner.parabola(z_opt, *fitparams)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=z_tun, y=Pz_tun, mode='markers', name='Data'))
            fig.add_trace(go.Scatter(x=z_fit_curve, y=P_fit_curve, mode='lines', name='Parabola fit'))
            fig.add_trace(go.Scatter(
                x=[z_opt], y=[P_at_opt], mode='markers',
                marker=dict(size=12, color='red', symbol='diamond'), name='Maximum',
            ))
            fig.update_layout(
                title_text=f"Z Scan - stage '{stage}'",
                xaxis_title='Z (\u03bcm)', yaxis_title='Power (a.u.)',
                width=460, height=460,
            )

            self._z_result = {'stage': stage, 'z_opt': z_opt}

            with output:
                output.clear_output(wait=True)
                print(f"Parabola fit maximum (stage '{stage}'): Z = {z_opt:.3f} \u03bcm "
                      f"(fitted power = {P_at_opt:.4g})")
                fig.show()

            result_label.value = f"Maximum at Z={z_opt:.3f} \u03bcm"
            move_button.disabled = False

        self._run_async(f"z scan '{stage}'", fn)

    def _on_move_zscan(self, result_label):
        if self._z_result is None:
            return
        stage = self._z_result['stage']
        z_opt = self._z_result['z_opt']

        def fn():
            self.stg.move_relative(stage, 'Z', z_opt, wait=True)
            result_label.value = f"Moved '{stage}' to Z={z_opt:.3f} \u03bcm"

        self._run_async(f"move '{stage}' to Z maximum", fn)
