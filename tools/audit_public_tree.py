"""Fail closed before a source-only export; report categories, never secret values."""
import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path, nargs='?', default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
root = args.directory.resolve()
ignored_dirs = {'.git', '__pycache__', 'node_modules', '.pytest_cache'}
forbidden_suffixes = {'.ipa', '.p12', '.p8', '.pem', '.key', '.mobileprovision', '.provisionprofile', '.ndjson'}
checks = [
    ('private_key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('github_token', re.compile(r'\b(?:ghp|gho|ghu|ghs)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b')),
    ('live_payment_key', re.compile(r'\b(?:sk_live_|rk_live_)[A-Za-z0-9]{16,}\b')),
    ('aws_access_key', re.compile(r'\bAKIA[A-Z0-9]{16}\b')),
    ('email_address', re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')),
    ('local_user_path', re.compile(r'(?:[A-Za-z]:[\\/]+Users[\\/]+|/Users/|/home/)[A-Za-z0-9_.-]+[\\/]')),
]
problems = []
files = 0
for path in sorted(root.rglob('*')):
    relative = path.relative_to(root)
    if not path.is_file() or any(part in ignored_dirs for part in relative.parts):
        continue
    files += 1
    name = relative.as_posix()
    if path.suffix.lower() in forbidden_suffixes or path.name in {'drover-packet.bin', '.env', 'artifact-url.txt'}:
        problems.append({'file': name, 'category': 'private_or_uncleared_asset'})
        continue
    try:
        content = path.read_text(encoding='utf-8')
    except (UnicodeError, OSError):
        continue
    for label, pattern in checks:
        if pattern.search(content):
            problems.append({'file': name, 'category': label})
result = {'passed': not problems, 'files_checked': files, 'findings': problems,
          'scope': 'Static source-only export guard; not a guarantee of all privacy or rights.'}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
