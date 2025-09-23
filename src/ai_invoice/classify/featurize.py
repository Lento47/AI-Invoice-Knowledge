from sklearn.feature_extraction.text import TfidfVectorizer


def build_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        max_features=5000,
        ngram_range=(1, 2),
    )
