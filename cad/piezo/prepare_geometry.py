"""Trace the exact planar guide union without a native CAD runtime."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'generated'

def boundaries(rectangles):
    xs = sorted({r[i] for r in rectangles for i in (0, 2)})
    ys = sorted({r[i] for r in rectangles for i in (1, 3)})
    cells = {(i,j) for i in range(len(xs)-1) for j in range(len(ys)-1)
             if any(a <= (xs[i]+xs[i+1])/2 <= c and b <= (ys[j]+ys[j+1])/2 <= d
                    for a,b,c,d in rectangles)}
    reached = set(); queue = [next(iter(cells))]
    while queue:
        cell = queue.pop()
        if cell in reached: continue
        reached.add(cell);i,j = cell
        queue.extend(n for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)) if n in cells and n not in reached)
    assert reached == cells, 'Guide contains disconnected regions'
    edges = {}
    for i,j in cells:
        candidates = [((i,j-1),(xs[i],ys[j]),(xs[i+1],ys[j])),
                      ((i+1,j),(xs[i+1],ys[j]),(xs[i+1],ys[j+1])),
                      ((i,j+1),(xs[i+1],ys[j+1]),(xs[i],ys[j+1])),
                      ((i-1,j),(xs[i],ys[j+1]),(xs[i],ys[j]))]
        for neighbor,a,b in candidates:
            if neighbor not in cells:
                assert a not in edges, 'Ambiguous point-only junction'
                edges[a] = b
    result = []
    while edges:
        start = min(edges);loop = [start];point = edges.pop(start)
        while point != start:
            loop.append(point);point = edges.pop(point)
        corners = [b for a,b,c in zip(loop[-1:]+loop[:-1],loop,loop[1:]+loop[:1])
                   if (b[0]-a[0])*(c[1]-b[1]) != (b[1]-a[1])*(c[0]-b[0])]
        result.extend([[list(a),list(b)] for a,b in zip(corners,corners[1:]+corners[:1])])
    area = sum((xs[i+1]-xs[i])*(ys[j+1]-ys[j]) for i,j in cells)
    return result, area

def guide(parameters, short=False):
    H = 25 if short else 35
    outer = 18 if short else 22
    inner = 7.5 if short else 10
    cy = 9.5 if short else 12
    t = parameters['leaf_t'];link = 13+parameters['leaf_L']
    boxes = [(-35,-H,35,-H+4),(-35,H-4,35,H),(-35,-H+4,-31,H-4),
             (31,-H+4,35,H-4),(-13,-cy,13,cy)]
    for sign in (-1,1):
        def mirror(r):
            a,b,c,d = r
            return r if sign < 0 else (-c,b,-a,d)
        boxes.extend(mirror(r) for r in [(-link-2,-outer-1.5,-link,outer+1.5),
                     (-13,outer-1.5,-10,H-4),(-13,-H+4,-10,-outer+1.5)])
        boxes.extend(mirror((-link,y-t/2,-13,y+t/2)) for y in (-outer,outer,-inner,inner))
    edges,area = boundaries(boxes)
    return dict(edges=edges, area=area, volume=area*parameters['guide_depth'], height=H*2, carriage_half=cy)

def main():
    OUT.mkdir(exist_ok=True)
    parameters = json.loads((ROOT/'parameters.json').read_text())
    assert 10 <= parameters['leaf_L'] <= 15, 'P0 planform sweep supports 10-15 mm leaves only'
    assert .2 <= parameters['leaf_t'] <= .8
    assert parameters['guide_depth'] == 6, 'P0 mounting heights require 6 mm depth; revise assembly before changing it'
    vendor = json.loads((ROOT/'vendor.json').read_text())
    actual = hashlib.sha256((ROOT/vendor['file']).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    assert actual == vendor['text_sha256_lf'], 'Vendor STEP changed; remeasure and update vendor.json before building'
    data = {'vendor': vendor['file'], 'guide_long': guide(parameters), 'guide_short': guide(parameters,True),
            'vendor_bounds': vendor['measured_bounds_mm'], 'parameters': parameters}
    (OUT/'geometry.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='edges'} for k,v in data.items() if k.startswith('guide_')}))

if __name__ == '__main__': main()
