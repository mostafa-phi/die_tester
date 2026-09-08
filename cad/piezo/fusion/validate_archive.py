"""Verify that the exported standalone native archive can be reopened."""
import adsk.core
import adsk.fusion
import json
from pathlib import Path

ROOT=Path(__PIEZO_ROOT__)

def run(_context: str):
    app=adsk.core.Application.get();original=app.activeDocument
    options=app.importManager.createFusionArchiveImportOptions(str(ROOT/'native/APA60S_Z_axis_P0.f3d'))
    doc=app.importManager.importToNewDocument(options)
    assert doc is not None
    d=adsk.fusion.Design.cast(app.activeProduct)
    result={'archive_reopened': True, 'components': d.allComponents.count,
            'bodies': sum(c.bRepBodies.count for c in d.allComponents), 'timeline': d.timeline.count}
    assert result['bodies']==5, 'Unexpected standalone module body inventory'
    (ROOT/'reports/archive_check.json').write_text(json.dumps(result,indent=2)+'\n')
    original.activate()
    print(json.dumps(result))
