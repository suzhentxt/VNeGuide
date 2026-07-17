---
license: cc-by-4.0
language:
- vi
tags:
- administrative
- vietnamese
- government
- procedures
size_categories:
- 1K<n<10K
---

# Vietnamese Administrative Procedures Dataset (Thủ Tục Hành Chính)

Vietnamese administrative procedures documentation from government sources.

## Dataset Details

| Property | Value |
|----------|-------|
| **Records** | 5,733 |
| **Size** | ~44 MB |
| **Language** | Vietnamese |
| **Last Updated** | 16/12/2025 |

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Procedure code (e.g., `1.000005`) |
| `title` | string | Procedure title |
| `text` | string | Full procedure content |
| `source` | string | Always `thutuchanhchinh` |

## Usage

```python
from datasets import load_dataset

ds = load_dataset("your-username/vietnamese-administrative-procedures")
print(ds["train"][0])
```

## Data Source

Administrative procedures (Thủ tục hành chính - TTHC) from Vietnamese government portals, containing detailed information about citizen services and procedures.
