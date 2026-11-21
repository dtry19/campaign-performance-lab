"""Download the version-pinned Criteo source release (not committed to Git)."""
from pathlib import Path
import hashlib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '904188a63cbad78bee43cd26ff5ee4ac77903986'
URL = f'https://huggingface.co/datasets/criteo/criteo-attribution-dataset/resolve/{REVISION}/criteo_attribution_dataset.tsv.gz'
SHA256 = '94ac7a465564349bc7ba008602211d5990a3c53cc133abc0aadef61ea2391a98'
DEFAULT_SOURCE = ROOT / 'data/source/criteo_attribution_dataset.tsv.gz'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def download():
    path = DEFAULT_SOURCE
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and digest(path) == SHA256:
        print(f'Already verified: {path}')
        return
    partial = path.with_suffix('.download')
    with urllib.request.urlopen(URL, timeout=90) as source, partial.open('wb') as dest:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            dest.write(chunk)
    if digest(partial) != SHA256:
        raise ValueError('Source SHA-256 mismatch; refusing to use this download')
    partial.replace(path)
    print(f'Downloaded and verified: {path}')

if __name__ == '__main__':
    download()
