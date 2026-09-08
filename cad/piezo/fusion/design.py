import adsk.core, adsk.fusion, json, math
from pathlib import Path

ROOT=Path(__PIEZO_ROOT__)
OUT=ROOT/'generated'
P=adsk.core.Point3D.create
V=adsk.core.Vector3D.create
VI=adsk.core.ValueInput.createByString
NEW=adsk.fusion.FeatureOperations.NewBodyFeatureOperation
CUT=adsk.fusion.FeatureOperations.CutFeatureOperation

def matrix(origin=(0,0,0),axes=((1,0,0),(0,1,0),(0,0,1))):
    m=adsk.core.Matrix3D.create()
    m.setWithCoordinateSystem(P(*(v/10 for v in origin)),*[V(*a) for a in axes])
    return m

def comp(parent,name,origin=(0,0,0),axes=((1,0,0),(0,1,0),(0,0,1))):
    o=parent.occurrences.addNewComponent(matrix(origin,axes))
    o.component.name=name
    return o.component

def sketch(comp,name,z=0):
    plane=comp.xYConstructionPlane
    if z:
        p=comp.constructionPlanes.createInput();p.setByOffset(plane,VI(f'{z} mm'))
        plane=comp.constructionPlanes.add(p);plane.isLightBulbOn=False
    s=comp.sketches.add(plane);s.name=name
    return s

def extrude(comp,s,name,depth,operation=NEW,expected_area=None):
    if expected_area is None:
        profile=max([s.profiles.item(i) for i in range(s.profiles.count)],key=lambda p:p.areaProperties().area)
    else:
        profile=min([s.profiles.item(i) for i in range(s.profiles.count)],key=lambda p:abs(p.areaProperties().area*100-expected_area))
        assert abs(profile.areaProperties().area*100-expected_area)<0.1, 'Profile mismatch'
    f=comp.features.extrudeFeatures.addSimple(profile,VI(depth),operation);f.name=name
    s.isLightBulbOn=False
    return f

def box(parent,name,bounds):
    x0,y0,z0,x1,y1,z1=bounds
    c=comp(parent,name)
    s=sketch(c,'Footprint',z0)
    s.sketchCurves.sketchLines.addTwoPointRectangle(P(x0/10,y0/10,0),P(x1/10,y1/10,0))
    extrude(c,s,name,f'{z1-z0} mm')
    return c

def hole_z(c,xy,r,z,depth,name):
    s=sketch(c,name,z)
    for x,y in xy:s.sketchCurves.sketchCircles.addByCenterRadius(P(x/10,y/10,0),r/10)
    profiles=adsk.core.ObjectCollection.create()
    for p in s.profiles:profiles.add(p)
    f=c.features.extrudeFeatures.addSimple(profiles,VI(f'{depth} mm'),CUT);f.name=name;s.isLightBulbOn=False

def guided_module(parent,name,gdata,origin,axes,app):
    c=comp(parent,name,origin,axes)
    c.description='CONCEPT P0: local Y is motion, local Z is guide depth. Sharp leaf roots and coupling require FEA/redesign before manufacture. No motion joints represent elastic deformation.'
    guide=comp(c,'01 Monolithic folded guide - NOT RELEASED')
    s=sketch(guide,'Folded guide planform - generated from geometry.json')
    s.isComputeDeferred=True
    for a,b in gdata['edges']:
        line=s.sketchCurves.sketchLines.addByTwoPoints(P(a[0]/10,a[1]/10,0),P(b[0]/10,b[1]/10,0))
        line.isFixed=True
    s.isComputeDeferred=False
    extrude(guide,s,'Guide depth','guide_depth',expected_area=gdata['area'])
    # Actuator lives above the guide face with four millimetres of clear space.
    cy=gdata['carriage_half']; bcenter=-cy-7.5; fixedpad=-cy-15
    fixed=box(c,'02 Fixed APA mounting pedestal',( -3,fixedpad-3,9,3,fixedpad,23))
    # A separate strap connects the pedestal to the fixed lower frame, clear above leaves.
    h=gdata['height']/2
    box(c,'03 Fixed pedestal support',(-3,min(-h,fixedpad-3),6,3,(-h+4 if h==25 else fixedpad),9))
    moving=box(c,'04 Carriage mounting land - coupling TBD',(-3,-cy,6,3,-cy+4,23))
    moving.description='Rigid placeholder. Replace with axially stiff angular/transverse relief coupling after vendor off-axis stiffness/limits are obtained.'
    actuator=comp(c,'05 CEDRAT APA60S vendor STEP',(0,bcenter,15))
    opts=app.importManager.createSTEPImportOptions(str(ROOT/DATA['vendor']))
    assert app.importManager.importToTarget(opts,actuator)
    # Four nominal clearance holes through stationary corner lands. Preliminary only.
    hole_z(guide,[(-33,-h+2),(33,-h+2),(-33,h-2),(33,h-2)],1.1,0,6,'M2 clearance - preliminary frame interface')
    outer=18 if h==25 else 22
    for sign in (-1,1):
        coords=[(-13,outer),(-11,outer),(-11,cy+2.25),(11,cy+2.25),(11,outer),(13,outer),(13,cy+.25),(-13,cy+.25)]
        st=sketch(guide,'Integral keeper stop - 250um nominal gap')
        coords=[(x,y*sign) for x,y in coords]
        for a,b in zip(coords,coords[1:]+coords[:1]):st.sketchCurves.sketchLines.addByTwoPoints(P(a[0]/10,a[1]/10,0),P(b[0]/10,b[1]/10,0))
        extrude(guide,st,'Keeper stop - handling only','guide_depth',adsk.fusion.FeatureOperations.JoinFeatureOperation)
    return c

def run(_context: str):
    global DATA
    DATA=json.loads((OUT/'geometry.json').read_text())
    app=adsk.core.Application.get()
    doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design=adsk.fusion.Design.cast(app.activeProduct)
    design.designType=adsk.fusion.DesignTypes.ParametricDesignType
    root=comp(design.rootComponent,'APA60S XYZ - P0 Packaging and Guide Concept')
    root.description='PRELIMINARY ONLY. X optical / Y lateral / Z up. 300 g capacity target, normal holder represented by an unverified lightweight envelope. No FEA or manufacturing release. See README in exported folder.'
    params=DATA['parameters']
    for name,value,comment in [('guide_depth',f"{params['guide_depth']} mm",'Drives native guide extrusion thickness; changing requires mounting redesign'),('leaf_thickness_nominal',f"{params['leaf_t']} mm",'Reference; regenerate from parameters.json'),('leaf_length_nominal',f"{params['leaf_L']} mm",'Reference; regenerate from parameters.json'),('maximum_payload',f"{params['maximum_payload_g']} g",'Maximum target, not demonstrated')]:
        unit='g' if name=='maximum_payload' else 'mm'
        design.userParameters.add(name,VI(value),unit,comment)
    base=box(root,'00 Coarse carriage adapter - preliminary',(-35,-35,0,35,35,4))
    hole_z(base,[(-10,-22.5),(-10,22.5),(10,-22.5),(10,22.5)],2.2,0,6,'LX20 nominal 20 x 45 M4 clearance pattern')
    box(root,'01 X fixed-frame support left',(-35,-35,4,35,-31,6))
    box(root,'02 X fixed-frame support right',(-35,31,4,35,35,6))
    xc=guided_module(root,'10 X AXIS - optical - outer',DATA['guide_long'],(0,0,6),((0,-1,0),(1,0,0),(0,0,1)),app)
    bridge=box(root,'11 X carriage central riser',(-7,-10,12,10,10,26))
    box(root,'12 X carriage bridge below Y frame',(-7,-35,26,10,35,29))
    box(root,'13 Y fixed frame rear seat',(-10,-35,29,10,-31,32))
    box(root,'14 Y fixed frame front seat',(-10,31,29,10,35,32))
    yc=guided_module(root,'20 Y AXIS - lateral - middle',DATA['guide_long'],(0,0,32),((1,0,0),(0,1,0),(0,0,1)),app)
    zsupport=box(root,'21 Y carriage to Z fixed frame pedestal',(-10,-8,38,32,8,56))
    zc=guided_module(root,'30 Z AXIS - vertical - inner',DATA['guide_short'],(26,0,81),((0,1,0),(0,0,1),(1,0,0)),app)
    holder=box(root,'40 Replaceable fiber nose - PLACEHOLDER',(32,-3,78,61,3,84))
    holder.description='Unconfirmed holder envelope. Optical center Z81, Y0. Real mass, clamp design, roll, protrusion and COM must replace this placeholder.'
    fiber=comp(root,'41 Fiber tip envelope - 125um diameter',(61,0,81),((0,1,0),(0,0,1),(1,0,0)))
    s=sketch(fiber,'Fiber cross-section');s.sketchCurves.sketchCircles.addByCenterRadius(P(0,0,0),0.00625)
    extrude(fiber,s,'Bare fiber 5 mm','5 mm')
    app.activeViewport.fit()
    info={'document':doc.name,'root':root.name,'components':design.allComponents.count,'occurrences':root.allOccurrences.count,'bodies':sum(c.bRepBodies.count for c in design.allComponents),'timeline':design.timeline.count}
    (OUT/'fusion_build_result.json').write_text(json.dumps(info,indent=2))
    print(json.dumps(info))
