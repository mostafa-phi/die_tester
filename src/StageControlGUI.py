import threading
import ipywidgets as widgets
from IPython.display import display


class StageControlGUI:
    """
    Interactive jog-control panel for the die tester stages.

    Gives independent X/Y/Z jog controls (type a distance in microns, click Move) for the
    input fiber (left / 'l') and output fiber (right / 'r')  stages, and a step-size /
    direction toggle for the chip ('m') stage -- its only axis is 'X'. The chip can be
    stepped by the fixed 8 or 254 micron waveguide pitch used elsewhere in the notebook
    (prep_next_waveguide / advance_chip in src/AutoAlignController.py), or by a custom
    typed amount.

    Usage:
        stage_gui = StageControlGUI(stg)
        stage_gui.display()
    """

    fiber_axes = ['X', 'Y', 'Z']
    chip_speed = 9  # matches stg.set_speed('m', 9) used elsewhere before chip moves
    chip_step_options = [8, 254, 'Custom']

    def __init__(self, die_tester_stage):
        self.stg = die_tester_stage
        # Serializes all stage commands: the 'l' and 'r' fiber stages share the same
        # Z-axis device (dev4), so concurrent Z moves from two panels could collide.
        self._move_lock = threading.Lock()
        self._all_move_buttons = []
        self.status_label = widgets.Label(value="Ready.")

    # ------------------------------------------------------------------
    def display(self):
        """
        Build and display the control panel.

        Does not return the widget -- returning it would cause Jupyter to auto-display it
        a second time (since the cell's last expression value gets shown too), producing a
        duplicate left/right/chip panel.
        """
        left_panel = self._build_fiber_panel('l', "Input Fiber - Left ('l')")
        right_panel = self._build_fiber_panel('r', "Output Fiber - Right ('r')")
        chip_panel = self._build_chip_panel()

        layout = widgets.VBox([
            widgets.HBox([left_panel, right_panel, chip_panel]),
            self.status_label,
        ])
        display(layout)

    # ------------------------------------------------------------------
    # Panel construction
    # ------------------------------------------------------------------
    def _build_fiber_panel(self, stage, title):
        rows = [widgets.HTML(f"<b>{title}</b>")]

        for axis in self.fiber_axes:
            # Plain Text (not FloatText): some ipywidgets/browser combinations treat a bare
            # "-" as a temporarily-invalid number and silently revert the numeric spinner
            # to its last valid value before the minus sign ever reaches the kernel, which
            # makes negative distances impossible to type. A text field has no such
            # validation -- we parse it ourselves in _on_fiber_move.
            entry = widgets.Text(
                value="0", description=f"{axis}:",
                layout=widgets.Layout(width='170px'),
            )
            button = widgets.Button(
                description="Move", button_style='primary',
                layout=widgets.Layout(width='70px'),
            )
            button.on_click(
                lambda b, s=stage, ax=axis, e=entry: self._on_fiber_move(s, ax, e)
            )
            self._all_move_buttons.append(button)
            rows.append(widgets.HBox([entry, button]))

        pos_label = widgets.Label(value="pos: (not read yet)")
        refresh_button = widgets.Button(
            description="Refresh position", layout=widgets.Layout(width='170px'),
        )
        refresh_button.on_click(lambda b, s=stage, pl=pos_label: self._on_refresh_position(s, pl))
        self._all_move_buttons.append(refresh_button)
        rows.append(widgets.HBox([refresh_button]))
        rows.append(pos_label)

        return widgets.VBox(
            rows,
            layout=widgets.Layout(border='1px solid gray', padding='6px', margin='4px', width='260px'),
        )

    def _build_chip_panel(self):
        title = widgets.HTML("<b>Chip ('m')</b>")
        step_toggle = widgets.ToggleButtons(
            options=self.chip_step_options, value=self.chip_step_options[0],
            description='Step (µm):',
        )
        custom_step_entry = widgets.Text(
            value="0", description='Custom (µm):',
            layout=widgets.Layout(width='170px'),
            disabled=(step_toggle.value != 'Custom'),
        )

        def on_step_toggle_change(change):
            custom_step_entry.disabled = (change['new'] != 'Custom')

        step_toggle.observe(on_step_toggle_change, names='value')

        dir_toggle = widgets.ToggleButtons(
            options=['+', '-'], value='+', description='Direction:',
        )
        move_button = widgets.Button(
            description="Move Chip", button_style='warning',
            layout=widgets.Layout(width='120px'),
        )
        pos_label = widgets.Label(value="pos: (not read yet)")
        refresh_button = widgets.Button(
            description="Refresh position", layout=widgets.Layout(width='170px'),
        )

        move_button.on_click(
            lambda b: self._on_chip_move(step_toggle, custom_step_entry, dir_toggle, pos_label)
        )
        refresh_button.on_click(lambda b: self._on_refresh_position('m', pos_label))

        self._all_move_buttons.extend([move_button, refresh_button])

        return widgets.VBox([
            title, step_toggle, custom_step_entry, dir_toggle,
            widgets.HBox([move_button, refresh_button]),
            pos_label,
        ], layout=widgets.Layout(border='1px solid gray', padding='6px', margin='4px', width='260px'))

    # ------------------------------------------------------------------
    # Move execution (threaded + serialized so the GUI never overlaps two stage commands)
    # ------------------------------------------------------------------
    def _set_buttons_enabled(self, enabled):
        for b in self._all_move_buttons:
            b.disabled = not enabled

    def _run_move(self, description, fn):
        """
        Run a blocking stage command (fn) on a background thread so the notebook/GUI stays
        responsive, and serialize commands with a lock since the fiber stages share a Z device.
        """
        if not self._move_lock.acquire(blocking=False):
            self.status_label.value = "Busy - a move is already in progress. Please wait."
            return

        self._set_buttons_enabled(False)
        self.status_label.value = f"Moving: {description} ..."

        def worker():
            try:
                fn()
                self.status_label.value = f"Done: {description}."
            except Exception as e:
                self.status_label.value = f"ERROR during {description}: {e}"
            finally:
                self._move_lock.release()
                self._set_buttons_enabled(True)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_fiber_move(self, stage, axis, entry):
        try:
            distance = float(entry.value)
        except ValueError:
            self.status_label.value = f"Invalid number for {stage} {axis}: '{entry.value}'"
            return

        def fn():
            self.stg.move_relative(stage, axis, distance, wait=True)

        self._run_move(f"stage '{stage}' axis {axis} by {distance:+g} um", fn)

    def _on_chip_move(self, step_toggle, custom_step_entry, dir_toggle, pos_label):
        if step_toggle.value == 'Custom':
            try:
                step = float(custom_step_entry.value)
            except ValueError:
                self.status_label.value = f"Invalid custom chip step: '{custom_step_entry.value}'"
                return
        else:
            step = step_toggle.value

        sign = 1 if dir_toggle.value == '+' else -1
        distance = sign * step

        def fn():
            self.stg.set_speed('m', self.chip_speed)
            self.stg.move_relative('m', 'X', distance, wait=True)
            pos = self.stg.query_position('m')
            pos_label.value = f"pos: {pos}"

        self._run_move(f"chip 'm' by {distance:+g} um", fn)

    def _on_refresh_position(self, stage, pos_label):
        def fn():
            pos = self.stg.query_position(stage)
            pos_label.value = f"pos: {pos}"

        self._run_move(f"query '{stage}' position", fn)
