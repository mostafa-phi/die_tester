import matplotlib.pyplot as plt
import numpy as np
import ipywidgets as widgets
from IPython.display import display
from matplotlib.patches import Polygon

class MultiImagePointSelector:
    # Configuration class variables
    point_marker_size = 4
    maximum_images_allowed = 100
    subplot_columns_limit = 3
    subplot_width_inches = 5
    subplot_height_inches = 4
    reset_buttons_per_row = 4
    point_marker_style = 'ro'  # 'r' = red, 'o' = circle
    grayscale_colormap = 'gray'
    polygon_edge_color = 'red'
    polygon_fill_color = 'red'
    polygon_edge_width = 2
    polygon_fill_alpha = 0.3
    
    def __init__(self, images: list, image_titles: list=None, image_descriptions: list=None, points_per_image=1, draw_polygon=False, fill_polygon=False):
        """
        Initialize the multi-image point selector.
        
        Parameters:
        images: list of numpy arrays representing the images
        image_titles: list of titles for each image (optional)
        image_descriptions: list of descriptions for each image (optional)
        points_per_image: number of points to select per image (default: 1)
        draw_polygon: whether to draw polygon connecting points (default: False)
        fill_polygon: whether to fill the polygon (default: False, only used if draw_polygon=True)
        """
        if len(images) > self.maximum_images_allowed:
            raise Exception(f"Number of images provided was greater than the maximum of {self.maximum_images_allowed}. Check your inputs or increase this number.")

        self.images = images
        self.n_images = len(images)
        self.points_per_image = points_per_image
        self.selection_enabled = False  # Track if point selection is enabled
        self.draw_polygon = draw_polygon
        self.fill_polygon = fill_polygon
        
        # Set default titles if none provided
        if image_titles is None:
            self.image_titles = [f"Image {i+1}" for i in range(self.n_images)]
        else:
            assert len(image_titles) == self.n_images, "Number of image titles must match the number of images!."
            self.image_titles = image_titles
        
        # Set default descriptions if none provided
        if image_descriptions is None:
            self.image_descriptions = [None for i in range(self.n_images)]
        else:
            assert len(image_descriptions) == self.n_images, "Number of image descriptions must match the number of images!."
            self.image_descriptions = image_descriptions
        
        # Initialize data structures
        self.selected_points = {}  # {image_idx: [point1, point2, ...]}
        self.markers = {}  # {image_idx: [marker1, marker2, ...]}
        self.polygons = {}  # {image_idx: polygon_patch}
        
        for i in range(self.n_images):
            self.selected_points[i] = []
            self.markers[i] = []
            self.polygons[i] = None
        
        self.fig = None
        self.axes = []
        self.control_box = None
        
    def display_interactive_plot(self):
        """Display all images with interactive point selection."""
        
        # Calculate subplot layout
        cols = min(self.subplot_columns_limit, self.n_images)
        rows = (self.n_images + cols - 1) // cols
        
        # Create figure with subplots
        self.fig, axes = plt.subplots(rows, cols, figsize=(self.subplot_width_inches*cols, self.subplot_height_inches*rows))
        
        # Handle single image case
        if self.n_images == 1:
            axes = [axes]
        elif rows == 1:
            axes = list(axes) if self.n_images > 1 else [axes]
        else:
            axes = axes.flatten()
        
        self.axes = axes
        
        # Display images
        for i, (image, title) in enumerate(zip(self.images, self.image_titles)):
            if i < len(self.axes):
                self.axes[i].imshow(image, cmap=self.grayscale_colormap if len(image.shape) == 2 else None)
                # Add description to title if available
                full_title = title
                if self.image_descriptions[i] is not None:
                    full_title += f"\n{self.image_descriptions[i]}"
                self.axes[i].set_title(full_title)
                self.axes[i].axis('on')
        
        # Hide unused subplots
        for i in range(self.n_images, len(self.axes)):
            self.axes[i].axis('off')
        
        # Connect click event
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        
        # Create widgets
        self.status_label = widgets.Label(value=self._get_status_text())
        self.progress_label = widgets.Label(value=self._get_progress_text())
        
        # Create coordinate labels for each image
        self.coord_labels = []
        for i in range(self.n_images):
            label = widgets.Label(value=f"{self.image_titles[i]}: No points selected")
            self.coord_labels.append(label)
        
        # Reset button
        self.reset_all_button = widgets.Button(description="Reset All", button_style='warning')
        self.reset_all_button.on_click(self._on_reset_all)
        
        # Toggle selection button
        if self.selection_enabled:
            self.toggle_selection_button = widgets.Button(description="Disable Selection", button_style='info')
        else:
            self.toggle_selection_button = widgets.Button(description="Enable Selection", button_style='success')
        self.toggle_selection_button.on_click(self._on_toggle_selection)
        
        # Toggle polygon button (only show if polygon drawing is enabled)
        if self.draw_polygon:
            self.toggle_polygon_button = widgets.Button(description="Hide Polygons", button_style='info')
            self.toggle_polygon_button.on_click(self._on_toggle_polygon)
            main_buttons = widgets.HBox([self.reset_all_button, self.toggle_selection_button, self.toggle_polygon_button])
        else:
            main_buttons = widgets.HBox([self.reset_all_button, self.toggle_selection_button])
        
        # Create individual reset buttons for each image
        self.reset_image_buttons = []
        for i in range(self.n_images):
            button = widgets.Button(
                description=f"Reset {self.image_titles[i]}", 
                button_style='primary'
            )
            button.on_click(lambda b, img_idx=i: self._reset_image(img_idx))
            self.reset_image_buttons.append(button)

        # Create layout
        coord_box = widgets.VBox(self.coord_labels)
        
        # Arrange reset buttons in rows if there are many images
        if self.n_images <= self.reset_buttons_per_row:
            reset_buttons_box = widgets.HBox(self.reset_image_buttons)
        else:
            # Split into multiple rows
            button_rows = []
            for i in range(0, self.n_images, self.reset_buttons_per_row):
                row_buttons = self.reset_image_buttons[i:i+self.reset_buttons_per_row]
                button_rows.append(widgets.HBox(row_buttons))
            reset_buttons_box = widgets.VBox(button_rows)
        
        self.control_box = widgets.VBox([
            self.status_label,
            self.progress_label,
            coord_box,
            main_buttons,
            reset_buttons_box
        ])
        
        # Display everything
        plt.tight_layout()
        plt.show()
        display(self.control_box)
        
        return self
    
    def _on_click(self, event):
        """Handle mouse click events."""
        # Check if selection is enabled
        if not self.selection_enabled:
            return
            
        # Find which axis was clicked
        clicked_axis_idx = None
        for i, ax in enumerate(self.axes[:self.n_images]):
            if event.inaxes == ax:
                clicked_axis_idx = i
                break
        
        if clicked_axis_idx is not None:
            self._handle_image_click(clicked_axis_idx, event)
    
    def _handle_image_click(self, image_idx, event):
        """Handle click on a specific image."""
        x, y = int(event.ydata), int(event.xdata)
        point = (x, y) 
        
        # Check if we can add more points to this image
        if len(self.selected_points[image_idx]) < self.points_per_image:
            # Add new point
            self.selected_points[image_idx].append(point)
            
            # Create marker
            marker = self.axes[image_idx].plot(y, x, self.point_marker_style, markersize = self.point_marker_size)[0]
            self.markers[image_idx].append(marker)
            
        else:
            # Replace the oldest point if at capacity
            # Remove oldest marker
            if self.markers[image_idx]:
                self.markers[image_idx][0].remove()
                self.markers[image_idx].pop(0)
                self.selected_points[image_idx].pop(0)
            
            # Add new point
            self.selected_points[image_idx].append(point)
            marker = self.axes[image_idx].plot(y, x, self.point_marker_style, markersize = self.point_marker_size)[0]
            self.markers[image_idx].append(marker)
        
        # Update polygon if enabled and we have enough points
        if self.draw_polygon:
            self._update_polygon(image_idx)
        
        self.fig.canvas.draw()
        self._update_display()
    
    def _update_polygon(self, image_idx):
        """Update polygon for a specific image."""
        # Remove existing polygon if it exists
        if self.polygons[image_idx] is not None:
            self.polygons[image_idx].remove()
            self.polygons[image_idx] = None
        
        # Only draw polygon if we have at least 3 points
        points = self.selected_points[image_idx]
        if len(points) >= 3:
            # Convert points to matplotlib coordinates (y, x) -> (x, y)
            polygon_coords = [(y, x) for x, y in points]
            
            # Create polygon patch
            polygon = Polygon(
                polygon_coords,
                closed=True,
                fill=self.fill_polygon,
                facecolor=self.polygon_fill_color if self.fill_polygon else 'none',
                edgecolor=self.polygon_edge_color,
                linewidth=self.polygon_edge_width,
                alpha=self.polygon_fill_alpha if self.fill_polygon else 1.0
            )
            
            # Add polygon to axis
            self.axes[image_idx].add_patch(polygon)
            self.polygons[image_idx] = polygon
    
    def _update_all_polygons(self):
        """Update polygons for all images."""
        if self.draw_polygon:
            for i in range(self.n_images):
                self._update_polygon(i)
    
    def _hide_all_polygons(self):
        """Hide all polygons."""
        for i in range(self.n_images):
            if self.polygons[i] is not None:
                self.polygons[i].remove()
                self.polygons[i] = None
    
    def _update_display(self):
        """Update all status displays."""
        self.status_label.value = self._get_status_text()
        self.progress_label.value = self._get_progress_text()
        
        # Update coordinate labels
        for i in range(self.n_images):
            points = self.selected_points[i]
            if not points:
                self.coord_labels[i].value = f"{self.image_titles[i]}: No points selected"
            else:
                points_str = ", ".join([f"({x}, {y})" for x, y in points]) # FLIP X AND Y to match the way images are indexed.
                self.coord_labels[i].value = f"{self.image_titles[i]} (y, x): {points_str}"
    
    def _get_status_text(self):
        """Generate status text based on current selection state."""
        total_selected = sum(len(points) for points in self.selected_points.values())
        total_needed = self.n_images * self.points_per_image
        
        selection_status = "" if self.selection_enabled else " [SELECTION DISABLED]"
        
        if total_selected == 0:
            return f"Select {self.points_per_image} point(s) on each of the {self.n_images} images{selection_status}"
        elif total_selected == total_needed:
            return f"All points selected! Points are ready for use.{selection_status}"
        else:
            return f"Continue selecting points... ({total_selected}/{total_needed} selected){selection_status}"
    
    def _get_progress_text(self):
        """Generate progress text."""
        total_selected = sum(len(points) for points in self.selected_points.values())
        total_needed = self.n_images * self.points_per_image
        return f"Progress: {total_selected}/{total_needed} points selected"
    
    def _reset_image(self, image_idx):
        """Reset selection for a specific image."""
        # Remove all markers for this image
        for marker in self.markers[image_idx]:
            marker.remove()
        
        # Remove polygon for this image
        if self.polygons[image_idx] is not None:
            self.polygons[image_idx].remove()
            self.polygons[image_idx] = None
        
        # Clear data
        self.markers[image_idx] = []
        self.selected_points[image_idx] = []
        
        self.fig.canvas.draw()
        self._update_display()
    
    def _on_reset_all(self, button):
        """Reset all selections."""
        for i in range(self.n_images):
            self._reset_image(i)
    
    def _on_toggle_selection(self, button):
        """Toggle point selection on/off."""
        self.selection_enabled = not self.selection_enabled
        
        if self.selection_enabled:
            self.toggle_selection_button.description = "Disable Selection"
            self.toggle_selection_button.button_style = 'info'
        else:
            self.toggle_selection_button.description = "Enable Selection"
            self.toggle_selection_button.button_style = 'success'
        
        self._update_display()
    
    def _on_toggle_polygon(self, button):
        """Toggle polygon visibility on/off."""
        if self.polygons and any(poly is not None for poly in self.polygons.values()):
            # Polygons are visible, hide them
            self._hide_all_polygons()
            self.toggle_polygon_button.description = "Show Polygons"
            self.toggle_polygon_button.button_style = 'success'
        else:
            # Polygons are hidden, show them
            self._update_all_polygons()
            self.toggle_polygon_button.description = "Hide Polygons"
            self.toggle_polygon_button.button_style = 'info'
        
        self.fig.canvas.draw()
    
    def get_points(self):
        """Get all currently selected points."""
        return {i: points.copy() for i, points in self.selected_points.items()}

    def get_points_by_image(self, image_idx):
        """Get points for a specific image."""
        return self.selected_points[image_idx].copy()
    
    def are_all_points_selected(self):
        """Check if all required points have been selected."""
        return all(len(points) == self.points_per_image 
                  for points in self.selected_points.values())
