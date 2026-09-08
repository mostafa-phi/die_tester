"""Called by build.py in Fusion; render the new design and its isolated Z module."""
import adsk.core
import adsk.fusion
from pathlib import Path

ROOT = Path(__PIEZO_ROOT__)

def camera(app, eye, target):
    c = app.activeViewport.camera
    c.eye = adsk.core.Point3D.create(*eye)
    c.target = adsk.core.Point3D.create(*target)
    c.upVector = adsk.core.Vector3D.create(0, 0, 1)
    c.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    c.isFitView = True
    app.activeViewport.camera = c
    app.activeViewport.refresh()

def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent.occurrences.item(0).component
    assert root.name.startswith('APA60S XYZ'), 'Expected the newly built piezo design'
    camera(app, (18, -22, 17), (0, 0, 5))
    assert app.activeViewport.saveAsImageFile(str(ROOT/'renders/assembly_preview.png'), 1400, 1100)
    visibility = [(o, o.isLightBulbOn) for o in root.occurrences]
    for occurrence, _ in visibility:
        occurrence.isLightBulbOn = occurrence.component.name.startswith('30 Z AXIS')
    camera(app, (16, -12, 12), (3, 0, 8))
    assert app.activeViewport.saveAsImageFile(str(ROOT/'renders/single_axis_preview.png'), 1200, 1100)
    for occurrence, state in visibility:
        occurrence.isLightBulbOn = state
    camera(app, (18, -22, 17), (0, 0, 5))
    print('Captured assembled and isolated-Z views; restored assembly visibility.')
