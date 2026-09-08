"""Independent build/verification entry point for the experimental Fusion piezo head."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'build_manifest.json'
OUTPUTS = [
    'generated/geometry.json',
    'native/APA60S_XYZ_P0.f3d', 'native/APA60S_Z_axis_P0.f3d',
    'STEP/APA60S_XYZ_P0.step', 'STEP/APA60S_Z_axis_P0.step',
    'STEP/APA60S_Z_guide_P0.step',
    'renders/assembly_preview.png', 'renders/single_axis_preview.png',
    'reports/verification.json', 'reports/screening.json', 'reports/archive_check.json',
]

def digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in ('.py', '.json', '.step', '.txt'):
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()

def sources() -> list[Path]:
    return sorted([*ROOT.glob('*.py'), *ROOT.glob('fusion/*.py'),
                   *ROOT.glob('simulations/*.py'), ROOT/'simulations/cases.json',
                   ROOT/'requirements.txt', ROOT/'APA60S.step', ROOT/'parameters.json', ROOT/'vendor.json'])

def prepare() -> None:
    subprocess.run([sys.executable, '-B', str(ROOT/'prepare_geometry.py')], check=True)
    subprocess.run([sys.executable, '-B', str(ROOT/'simulations/screening.py')], check=True)

def write_manifest() -> None:
    verification = json.loads((ROOT/'reports/verification.json').read_text())
    if verification['interferences']:
        raise RuntimeError('Nominal interferences remain; see reports/verification.json')
    data = {
        'schema': 1, 'design_revision': 'P0', 'status': 'concept_not_manufacturing_release',
        'built_utc': datetime.now(timezone.utc).isoformat(),
        'inputs': {p.relative_to(ROOT).as_posix(): digest(p) for p in sources()},
        'outputs': {p: digest(ROOT/p) for p in OUTPUTS},
        'validation_scope': 'Nominal interference, archive export, analytical screening; no FEA or station sweep.',
    }
    MANIFEST.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')

def check() -> int:
    if not MANIFEST.exists():
        print('No piezo manifest. Run --fusion to create a verified build.'); return 1
    manifest = json.loads(MANIFEST.read_text())
    problems = []
    actual_sources = {p.relative_to(ROOT).as_posix() for p in sources()}
    if actual_sources != set(manifest['inputs']):
        problems.append('Source inventory changed')
    for kind in ('inputs', 'outputs'):
        for name, expected in manifest[kind].items():
            p = ROOT/name
            if not p.exists() or digest(p) != expected:
                problems.append(f'{kind}: missing or changed {name}')
    if problems:
        print('\n'.join(problems)); return 1
    print('PASS: piezo sources and outputs match the independent P0 manifest.')
    print('This is provenance verification, not a payload, motion or FEA certification.')
    return 0

async def fusion_build(url: str) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    log = []
    async with streamablehttp_client(url) as (reader, writer, _):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            for filename in ('design.py', 'export_verify.py', 'validate_archive.py', 'capture.py'):
                script = (ROOT/'fusion'/filename).read_text(encoding='utf-8')
                script = script.replace('__PIEZO_ROOT__', repr(str(ROOT)))
                result = await session.call_tool('fusion_mcp_execute', {
                    'featureType': 'script', 'object': {'script': script}})
                record = result.model_dump(mode='json'); log.append({'script': filename, 'result': record})
                (ROOT/'reports/fusion_run.json').write_text(json.dumps(log, indent=2), encoding='utf-8')
                if result.isError:
                    raise RuntimeError(f'{filename}: MCP error; see reports/fusion_run.json')
                success = False
                for block in result.content:
                    if block.type != 'text': continue
                    payload = json.loads(block.text)
                    if payload.get('success') is False:
                        raise RuntimeError(f"{filename}: {payload.get('error', payload)}")
                    success |= payload.get('success') is True
                    print(payload.get('message', block.text), flush=True)
                if not success:
                    raise RuntimeError(f'{filename}: no explicit Fusion success response')
    write_manifest()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--prepare', action='store_true', help='Regenerate guide geometry and analytical screening only')
    modes.add_argument('--fusion', action='store_true', help='Prepare, create a NEW Fusion document, verify, export, render and record manifest')
    modes.add_argument('--check', action='store_true', help='Read-only provenance check; no Fusion connection required')
    parser.add_argument('--url', default=os.environ.get('FUSION_MCP_URL'), help='Fusion native MCP URL; alternatively set FUSION_MCP_URL')
    args = parser.parse_args()
    if args.check: return check()
    if args.fusion and not args.url: parser.error('--fusion requires --url or FUSION_MCP_URL')
    prepare()
    if args.fusion: asyncio.run(fusion_build(args.url))
    else: print('Prepared only. Existing Fusion exports may now be stale; run --fusion before sharing a new revision.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
