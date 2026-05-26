# Installation

## Requirements

- Python >= 3.12
- MongoDB >= 4.0 (transactions require a replica set)
- `motor`, `pymongo`, `pydantic` (installed automatically)

## Install

```bash
pip install vellum-odm
```

## Dependencies

Vellum depends on:

| Package | Version | Purpose |
|---|---|---|
| `pydantic` | >= 2.0 | Data validation and settings |
| `motor` | >= 3.2, < 4.0 | Async MongoDB driver |
| `pymongo` | >= 4.0, < 5.0 | Sync MongoDB driver (used by Motor) |
| `cryptography` | >= 44.0 | Fernet encryption for `EncryptedField` |

## Development

```bash
git clone https://github.com/wailbentafat/Vellum
cd Vellum
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Verify

```python
from vellum import VellumBaseModel
print(f"Vellum {VellumBaseModel.__module__}")
```
