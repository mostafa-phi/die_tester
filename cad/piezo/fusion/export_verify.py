import adsk.core, adsk.fusion, json
from pathlib import Path
OUT=Path(__PIEZO_ROOT__)

def identify(e):
    ctx=e.assemblyContext
    if ctx:return ctx.fullPathName
    return e.objectType+':'+e.name

def run(_context: str):
    app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct)
    for occ in d.rootComponent.allOccurrences:
        for b in occ.component.bRepBodies:b.name=occ.fullPathName
    entities=adsk.core.ObjectCollection.create();bodydata=[]
    for occ in d.rootComponent.allOccurrences:
        for body in occ.bRepBodies:
            entities.add(body);b=body.boundingBox
            bodydata.append({'path':occ.fullPathName,'volume_mm3':body.volume*1000,'bounds_mm':[v*10 for p in (b.minPoint,b.maxPoint) for v in (p.x,p.y,p.z)]})
    inp=d.createInterferenceInput(entities);inp.areCoincidentFacesIncluded=False
    results=d.analyzeInterference(inp)
    conflicts=[{'one':identify(r.entityOne),'two':identify(r.entityTwo),'volume_mm3':r.interferenceBody.volume*1000} for r in results]
    report={'body_count':entities.count,'interferences':conflicts,'bodies':bodydata,'timeline':d.timeline.count}
    (OUT/'reports'/'verification.json').write_text(json.dumps(report,indent=2))
    em=d.exportManager
    assert em.execute(em.createSTEPExportOptions(str(OUT/'STEP'/'APA60S_XYZ_P0.step')))
    assert em.execute(em.createFusionArchiveExportOptions(str(OUT/'native'/'APA60S_XYZ_P0.f3d')))
    zc=next(c for c in d.allComponents if c.name.startswith('30 Z AXIS'))
    assert em.execute(em.createSTEPExportOptions(str(OUT/'STEP'/'APA60S_Z_axis_P0.step'),zc))
    assert em.execute(em.createFusionArchiveExportOptions(str(OUT/'native'/'APA60S_Z_axis_P0.f3d'),zc))
    guide=next(o.component for o in zc.occurrences if o.component.name.startswith('01 Monolithic'))
    assert em.execute(em.createSTEPExportOptions(str(OUT/'STEP'/'APA60S_Z_guide_P0.step'),guide))
    print(json.dumps({'body_count':entities.count,'interferences':conflicts,'timeline':d.timeline.count}))
