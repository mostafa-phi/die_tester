import numpy as np
from typing import *
import cv2 as cv
from tqdm import tqdm
import matplotlib.pyplot as plt

from src.RealtimeVideoCapture import RealtimeVideoCapture
from src.InteractivePlots import MultiImagePointSelector
from src.DieTesterInstrument import DieTesterStage

class SoftwareFence:
    calibration_image_index = 0  # which image (from the calibration process) to display to the user who selects the fiber tip.

    def __init__(self, die_tester_stage: DieTesterStage, cap: RealtimeVideoCapture):
        self.stg = die_tester_stage
        self.cap = cap
        self.Zmove_selector = None

        self.Zcal_selector = None
        self.calibration_images = None
        self.calibration_distances = None

    # How images are captured
    def capture_image(self, num_mean_captures):
        img = self.cap.mean_capture(num_mean_captures, convert_to_grayscale=False)
        return img
        
    def new_movement_selection(self, num_mean_captures=10):
        """Select points for point-and-click movement."""
        img = self.capture_image(num_mean_captures)

        images = [
            img,
            img,
        ]
        descriptions = [
            "Please select the location of the fibertip.",
            "Please select the location you want to move to.",
        ]
        self.Zmove_selector = MultiImagePointSelector(images, image_descriptions=descriptions, points_per_image=1)
        return self.Zmove_selector.display_interactive_plot()
    
    def _capture_motion_data(self, stage, axis, distance, extra_backup_distance, num_steps, num_mean_captures):
        self.stg.move_relative(stage, axis, - (distance + extra_backup_distance), wait=True)
        img_bg = self.capture_image(num_mean_captures)
        self.stg.move_relative(stage, axis, extra_backup_distance, wait=True)

        img_list = []
        for _ in tqdm(range(num_steps)):
            self.stg.move_relative(stage, axis, distance / num_steps, wait=True)
            img = self.capture_image(num_mean_captures)
            img_list.append(
                cv.absdiff(img, img_bg)
            )

        img_list = np.array(img_list)
        dist_list = np.array([distance / num_steps * (i + 1) for i in range(num_steps)])

        return img_list, dist_list

    
    def run_calibration(self, stage, distance, extra_backup_distance, num_steps, num_mean_captures=10, axis='Z'):
        """
        Start a new distance calibration
            stage: 'l' or 'r'
            distance: Distance to travel in microns
            extra_backup_distance: extra clearance required to get fibertip out of frame
            num_steps: Number of steps equals number of images taken.
        """

        assert axis.upper() != 'Z' or (distance > 0 and extra_backup_distance > 0), "A negative distance in the 'Z' direction will initially move the fiber towards the waveplate and IS DANGEROUS"
        
        # Capture motion data
        img_list, dist_list = self._capture_motion_data(stage, axis, distance, extra_backup_distance, num_steps, num_mean_captures)
        self.calibration_images = img_list
        self.calibration_distances = dist_list

        # Display images in a selector.
        images = [
            img_list[self.calibration_image_index]
        ]
        descriptions = [
            "Please select a bounding box around the fibertip."
        ]
        self.Zcal_selector = MultiImagePointSelector(
            images, 
            image_descriptions = descriptions,
            points_per_image = 4,
            draw_polygon = True
        )
        return self.Zcal_selector.display_interactive_plot()

    def calculate_move(self, stage, microns_per_pixel, tip_angle):
        """Return the relative movement required in the form (X, Z)."""
        # Calculate relative motion
        if self.Zmove_selector is None or not self.Zmove_selector.are_all_points_selected():
            raise Exception("Not enough points to complete calculation. Please select all of the points.")
        
        # Grab parity
        if stage == 'l':
            parity = [
                self.stg.dev1.stage_parity[0], # x parity for 'l' stage
                self.stg.dev4.stage_parity[0], # z parity for 'l' stage
            ]
        elif stage == 'r':
            parity = [
                self.stg.dev2.stage_parity[0], # x parity for 'r' stage
                 - self.stg.dev4.stage_parity[1], # z parity for 'r' stage; Z is flipped with respect to image.
            ]
        else:
            raise ValueError("Invalid stage specification!")

        points = self.Zmove_selector.get_points()
        p_tip = np.array( points[0][0] )
        p_move =  np.array( points[1][0] )

        movement_delta = microns_per_pixel * (p_move - p_tip)
        movement_matrix = np.array([ # 2x2 matrix with columns representing a single "step" along z or x (row 1: step along x, row 2: step along Z. Note that "positive X" points down, hence why we invert the cos instead of the sin on column 1.)
            [ - parity[0] * np.cos(tip_angle), parity[1] * np.sin(tip_angle)   ], 
            [   parity[0] * np.sin(tip_angle), parity[1] * np.cos(tip_angle)   ] 
        ])

        move = np.linalg.solve(movement_matrix, movement_delta)
        return move
    
    def calculate_calibration(self, stage):
        """
        Calculate microns per pixel and tip angle from distance calibration.
        """
        if self.Zcal_selector is None or not self.Zcal_selector.are_all_points_selected():
            raise Exception("Not enough points to complete calculation. Please select all of the points.")
        if self.calibration_distances is None or self.calibration_images is None:
            raise Exception("There are no calibration images or distances available!")

        dist_list = self.calibration_distances

        points = np.array(self.Zcal_selector.get_points()[0])
        Xmin = np.min(points[:, 0])
        Zmin = np.min(points[:, 1])
        Xmax = np.max(points[:, 0])
        Zmax = np.max(points[:, 1])
        template = self.calibration_images[self.calibration_image_index][Xmin:Xmax, Zmin:Zmax]

        residuals = [
            cv.matchTemplate(i.astype(np.uint8), template.astype(np.uint8), cv.TM_CCOEFF_NORMED) for i in self.calibration_images
        ]
        tip_list = np.array([ # Note: this is the top left corner of the template as opposed to the center of the template.
            np.unravel_index(np.argmax(res, axis=None), res.shape) for res in residuals
        ])

        tip_magnitude = np.sqrt(
            (tip_list[:, 0] - tip_list[0, 0])**2 + 
            (tip_list[:, 1] - tip_list[0, 1])**2
        )
        (signed_mpp, _), mpp_MSE, _, _, _ = np.polyfit(tip_magnitude, dist_list, deg=1, full=True)

        microns_per_pixel = abs(signed_mpp)  # we want magnitude

        # tip angles from horizontal (note that when plotting, down is positive angle)

        if stage == 'l':            
            tip_ang_list = np.atan2( 
                tip_list[:, 0] - tip_list[0, 0],    # X
                tip_list[:, 1] - tip_list[0, 1]     # Z
            )
        elif stage == 'r':
            tip_ang_list = np.atan2( 
                tip_list[:, 0] - tip_list[0, 0],    # X
                tip_list[0, 1] - tip_list[:, 1]     # Z is flipped
            )
        else:
            raise ValueError("Invalid stage specification!")

        
        tip_angle = np.mean(tip_ang_list)
        

        print(f"Microns per pixel: {microns_per_pixel:0.3f} with MSE of {mpp_MSE[0]:0.2f}")
        print(f"Angle of tip with respect to horizontal: {tip_angle:0.3f} radians ({tip_angle * 180 / np.pi : 0.2f} degrees).")
        
        return {
            'microns_per_pixel': microns_per_pixel,
            'tip_angle': tip_angle,
            'fibertip_visualization': self.fibertip_visualization(tip_list, dist_list)
        }

    def fibertip_visualization(self, tip_list, dist_list):
        "Visualization of how the fibertip changes over time. Points in the form (X, Z)."
        fig, axs = plt.subplots(1, 2, figsize=(12, 4))

        fig.suptitle('Fibertip Pixel vs Micron Coordinates')
        axs[0].scatter(dist_list, tip_list[:, 1], c=dist_list)
        axs[0].set_xlabel("Distance (microns)")
        axs[0].set_ylabel("Z (pixels)")

        axs[1].scatter(dist_list, tip_list[:, 0], c=dist_list)
        axs[1].set_xlabel("Distance (microns)")
        axs[1].set_ylabel("X (pixels)")

        return fig
