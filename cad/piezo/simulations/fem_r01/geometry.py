"""Fusion script: derive the single-axis FEM geometry from the released P0 export.

Run via native Fusion MCP after replacing __PIEZO_ROOT__ with this checkout's path.
P0 assembly geometry is deliberately not overwritten.
"""
import adsk.core, adsk.fusion, json
from pathlib import Path

ROOT=Path(__PIEZO_ROOT__)
OUT=ROOT/'simulations/fem_r01'
P=adsk.core.Point3D.create
VI=adsk.core.ValueInput.createByString

def split_patch(component,body,y,x0,x1,z0,z1,name):
    faces=adsk.core.ObjectCollection.create()
    for f in body.faces:
        if f.geometry.surfaceType==adsk.core.SurfaceTypes.PlaneSurfaceType and abs(f.pointOnFace.y*10-y)<1e-5:
            n=f.geometry.normal
            if abs(n.y)>.99:faces.add(f)
    assert faces.count==1, f'{name}: expected one planar starting face, found {faces.count}'
    pi=component.constructionPlanes.createInput()
    pi.setByOffset(component.xZConstructionPlane,VI(f'{-y} mm'))
    plane=component.constructionPlanes.add(pi);plane.isLightBulbOn=False
    s=component.sketches.add(plane);s.name=name
    # Convert actual model points to avoid relying on the XZ sketch's handedness.
    a=s.modelToSketchSpace(P(x0/10,y/10,z0/10));b=s.modelToSketchSpace(P(x1/10,y/10,z1/10))
    lines=s.sketchCurves.sketchLines.addTwoPointRectangle(a,b)
    curves=adsk.core.ObjectCollection.create()
    for line in lines:curves.add(line)
    inp=component.features.splitFaceFeatures.createInput(faces,curves,False)
    feature=component.features.splitFaceFeatures.add(inp);feature.name=name;s.isLightBulbOn=False

def run(_context: str):
    OUT.mkdir(exist_ok=True)
    app=adsk.core.Application.get()
    options=app.importManager.createSTEPImportOptions(str(ROOT/'STEP/APA60S_Z_guide_P0.step'))
    doc=app.importManager.importToNewDocument(options)
    d=adsk.fusion.Design.cast(app.activeProduct);d.designType=adsk.fusion.DesignTypes.ParametricDesignType
    bodies=[b for c in d.allComponents for b in c.bRepBodies]
    assert len(bodies)==1
    body=bodies[0];c=body.parentComponent;body.name='FEM R01 Z guide - 0.5mm roots'
    edges=adsk.core.ObjectCollection.create()
    targets_y=[v+s*.25 for v in (-18,-7.5,7.5,18) for s in (-1,1)]
    for edge in body.edges:
        a=edge.startVertex.geometry;b=edge.endVertex.geometry
        if abs(a.x-b.x)>1e-7 or abs(a.y-b.y)>1e-7 or abs(abs(a.z-b.z)-.6)>1e-7:continue
        if min(abs(abs(a.x*10)-v) for v in (13,27))<1e-5 and min(abs(a.y*10-v) for v in targets_y)<1e-5:edges.add(edge)
    assert edges.count==32, f'Expected 32 leaf-root edges; found {edges.count}'
    fi=c.features.filletFeatures.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges,VI('0.5 mm'),False)
    fillet=c.features.filletFeatures.add(fi);fillet.name='32 leaf roots R0.5 mm'
    # Bonded/monolithic surrogate for the P0 output mounting land.
    pi=c.constructionPlanes.createInput();pi.setByOffset(c.xYConstructionPlane,VI('6 mm'))
    plane=c.constructionPlanes.add(pi);plane.isLightBulbOn=False
    s=c.sketches.add(plane);s.name='P0 carriage land footprint'
    s.sketchCurves.sketchLines.addTwoPointRectangle(P(-.3,-.95,0),P(.3,-.55,0))
    ex=c.features.extrudeFeatures.addSimple(s.profiles.item(0),VI('17 mm'),adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ex.name='Bonded-land surrogate';s.isLightBulbOn=False
    body=c.bRepBodies.item(0)
    split_patch(c,body,-9.5,-1.25,1.25,12.5,17.5,'APA load patch 2.5x5mm at Z15')
    split_patch(c,body,-25,-8,8,0,6,'Rigid fixture patch 16x6mm')
    material=app.materialLibraries.itemByName('Fusion Material Library').materials.itemByName('Aluminum 7075')
    body.material=material
    properties=[]
    for p in material.materialProperties:
        if hasattr(p,'value'):properties.append({'id':p.id,'name':p.name,'value':str(p.value),'units':getattr(p,'units',None)})
    report={'source':'STEP/APA60S_Z_guide_P0.step','root_radius_mm':.5,'filleted_edges':32,
            'volume_mm3':body.volume*1000,'material':material.name,'material_properties':properties,
            'force_patch_mm':{'x':[-1.25,1.25],'y':-9.5,'z':[12.5,17.5]},
            'fixture_patch_mm':{'x':[-8,8],'y':-25,'z':[0,6]},
            'notes':['Guide only plus bonded output-land surrogate','Local Y is driven axis, local Z is depth','No payload, no gravity, no APA stiffness in initial compliance study']}
    (OUT/'geometry_report.json').write_text(json.dumps(report,indent=2))
    em=d.exportManager
    assert em.execute(em.createSTEPExportOptions(str(OUT/'guide_r01.step')))
    assert em.execute(em.createFusionArchiveExportOptions(str(OUT/'guide_r01.f3d')))
    app.activeViewport.fit()
    print(json.dumps({'filleted_edges':32,'volume_mm3':body.volume*1000,'material':material.name,'products':[(p.productType,p.objectType) for p in doc.products]}))
