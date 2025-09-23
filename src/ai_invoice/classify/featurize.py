```python
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer


def build_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        max_features=5000,
        ngram_range=(1, 2),
        strip_accents="unicode",
    )
```
