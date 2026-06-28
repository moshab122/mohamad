# mohamad
rand love mohamad

## Username availability validator

Script: `/home/runner/work/mohamad/mohamad/username_validator.py`

### Install dependency

```bash
pip install aiohttp
```

### Quick check (generate first identifier for length 4)

```bash
python /home/runner/work/mohamad/mohamad/username_validator.py --length 4 --first-only
```

### Run full validator

```bash
python /home/runner/work/mohamad/mohamad/username_validator.py \
  --length 4 \
  --public-url "https://example.com/users/{identifier}" \
  --fallback-url "https://example.com/api/users/{identifier}" \
  --concurrency 10 \
  --delay 0.2
```

Available validated identifiers are appended to `validated_identifiers.txt`.
