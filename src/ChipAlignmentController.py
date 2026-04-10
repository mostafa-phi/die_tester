import cv2 as cv
import numpy as np
import time

import matplotlib.pyplot as plt

from src.InteractivePlots import MultiImagePointSelector

## For Thorlabs camera motors
# from Thorlabs.MotionControl.DeviceManagerCLI import *
# from Thorlabs.MotionControl.GenericMotorCLI import *
# from Thorlabs.MotionControl.KCube.DCServoCLI import *
# from System import Decimal

## for alternative Thorlabs rotational stage (not Suruga-Seiki)
# from Thorlabs.Elliptec.ELLO_DLL import * 

class ChipAlignmentController:
    def __init__(self, die_tester_stage, cap):
        self.template_selector = None
        self.template_image = None
        self.stg = die_tester_stage
        self.cap = cap                  # camera capture
    
    # How images are captured in the calibration process
    def capture_image(self, num_mean_captures):
        img = self.cap.mean_capture(num_mean_captures)
        return img
    
    def run_angle_calibration(self, mainX, calX, camera_focus_prompt=False, num_mean_captures=10, pause_time=0.5):
        """
        Run angle calibration
            mainX: Magnitude and direction of the main movement (or total movement). Should be around 1cm.
            calX: Magnitude and direction of the image calibration movemetn. Should be as high as possible while keeping the pattern in frame, but anything over 100 microns is fine.
            camera_focus_prompt: Defaults to False. Whether to wait at the second calibration marker for the user to re-focus the camera. (Use if focus is different)
            num_mean_captures: Defaults to 10. Number of images the camera averages together.
            pause_time: Defaults to 0.5. Amount of time the camera waits (for vibrations to stop) before taking the image
        """
        move_calibration = np.array([calX,  0])
        move_main        = np.array([mainX, 0])

        img_c0 = self.capture_image(num_mean_captures)

        print("Starting Calibration Movement...")
        self.stg.move_relative('m', 'X', move_calibration[0], wait=True)
        time.sleep(pause_time)
        img_c0_move = self.capture_image(num_mean_captures)

        print("Calibration movement done. Starting main movement...")
        self.stg.move_relative('m', 'X', move_main[0]-move_calibration[0], wait=True)
        if camera_focus_prompt:
            input("Press enter once you have the camera in focus. ")
        else:
            time.sleep(pause_time)
        img_c1 = self.capture_image(num_mean_captures)

        print("All images aquired. Moving back to starting position.")
        self.stg.move_relative('m', 'X', -move_main[0], wait=False)

        print("Matching calibration centers...")        
        # pattern center in image coordinates
        c0      = np.array( self.match_pattern_center(img_c0)       )
        c0_move = np.array( self.match_pattern_center(img_c0_move)  )
        c1      = np.array( self.match_pattern_center(img_c1)       )

        print("Generating visualization of calibration centers...")
        fig, axs = plt.subplots(1, 3, figsize=(12,4))

        axs[0].imshow(img_c0)
        axs[0].scatter(c0[1], c0[0], c='r')
        axs[0].set_title("Center 0")
        axs[1].imshow(img_c0_move)
        axs[1].scatter(c0_move[1], c0_move[0], c='r')
        axs[1].set_title("Center 0 After Calibration Move")
        axs[2].imshow(img_c1)
        axs[2].scatter(c1[1], c1[0], c='r')
        axs[2].set_title("Center 1")

        print("Calculating rotation...")
        deg = self.calculate_rotation(
            move_calibration,
            move_main, 
            c0,
            c0_move,
            c1,
        )
        print(F"Done. Optimal rotation is {deg:0.4f} degrees.")

        # Show figure
        plt.show()
        return deg

    def new_template_selection(self, img):
        self.template_selector = MultiImagePointSelector(
            images = [img],
            image_titles = ["Image 1"],
            image_descriptions=["Please select precisely the four corners of the four-square calibration patch."],
            points_per_image=4,
            draw_polygon=True,
        )

        return self.template_selector.display_interactive_plot()

    
    def generate_template(self, img, border_pixel_offset=10):
        """
        Generate template
            img: Full image used in template selection
        """
        if not self.template_selector.are_all_points_selected() or self.template_selector is None:
            raise Exception("Please select all of the points in template selection graph.")
        
        corner_points = np.array(
            self.template_selector.get_points()[0]
        )
        Xmin = np.min(corner_points[:, 0]) - border_pixel_offset
        Zmin = np.min(corner_points[:, 1]) - border_pixel_offset
        Xmax = np.max(corner_points[:, 0]) + border_pixel_offset
        Zmax = np.max(corner_points[:, 1]) + border_pixel_offset
        
        self.template_image = img[Xmin:Xmax, Zmin:Zmax]
        print("Success! New template set.")
        return self.template_image

    def match_pattern_center(self, img):
        """Take picture, match pattern with the appropriate template photo, and return the coordinates of the center."""
        if self.template_image is None:
            raise ValueError("Please set a template image first.")
        
        assert img.dtype == self.template_image.dtype and len(img.shape) == len(self.template_image.shape), "Make sure the images from the camera and the template image have the same type and number of channels!"

        h, w = self.template_image.shape[:2]

        res = cv.matchTemplate(img, self.template_image, cv.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv.minMaxLoc(res)
        set_center = np.array([
            max_loc[1] + h / 2,  # image vertical axis, world "x" axis
            max_loc[0] + w / 2,  # image horizontal axis, world "y" axis
        ])

        return set_center
    
    def calculate_rotation(self, move_calibration, move_main, c0, c0_move, c1, image_parity = np.array([1, -1])):

        ## Notes:
        # image_parity: Used to give the center coordinates the same parity as world space, where positive X is towards the camera gantry.
        #
        # We want the angle between the vector connecting the two centers and the baseline calibration vector (lying along the x axis)
        # v1 (world space vector from center 0 -> center 1) equals the main movement plus the micron distance of the change in image centers x_p * (c1 - c0)
        # v2 (world space vector of the calibration movement) just equals the calibration movement. We don't have to consider the center positions because we're working with the same center.
        #   - We can use the change in center position to calculate the microns per pixel of resolution of the camera.

        c0      = np.multiply(image_parity, c0)         # Center 0 (intital center) on image
        c0_move = np.multiply(image_parity, c0_move)    # Center 0 after calibration move
        c1      = np.multiply(image_parity, c1)         # Center 1 (center on other corner of chip after main move)
        
        # microns per pixel = |micron distance| / |pixel distance|
        x_p = np.sqrt( 
            move_calibration[0]**2 + move_calibration[1]**2 
        ) / np.sqrt( 
            (c0_move[0]-c0[0])**2 + (c0_move[1]-c0[1])**2 
        )  
        
        v1 = move_main + x_p * (c1 - c0)  # large
        v2 = move_calibration

        v1_mag = np.sqrt(v1[0]**2 + v1[1]**2)
        v2_mag = np.sqrt(v2[0]**2 + v2[1]**2)

        # dot product to determine angle
        angle_rad = np.acos(
            np.dot(v1, v2) / (v1_mag * v2_mag)
        )
        angle_deg=angle_rad * (180 / np.pi)

        # cross product to determine sign of the angle from main motion (v1) -> calibration motion (v2) (this is the angle we have to move)
        v1_3d = np.append(v1, 0)
        v2_3d = np.append(v2, 0)
        cross = np.cross(v1_3d, v2_3d)
        if cross[2] < 0: # cross product is along 3rd axis; sign of normal vector determines sign of rotation.
            angle_deg = -angle_deg

        return angle_deg


