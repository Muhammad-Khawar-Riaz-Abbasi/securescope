from app.analyzer import analyze_password, sha1_prefix


def test_short_contextual_password_is_flagged() -> None:
    result = analyze_password("Alice123", ["Alice", "alice@example.com"])
    assert result.label in {"critical", "weak", "fair"}
    assert {finding.code for finding in result.findings} >= {"short", "context"}


def test_long_passphrase_has_positive_signal() -> None:
    result = analyze_password("correct horse battery staple!", [])
    assert result.length >= 16
    assert any(finding.code == "length" for finding in result.findings)


def test_hash_prefix_is_k_anonymous_shape() -> None:
    prefix, suffix = sha1_prefix("password")
    assert len(prefix) == 5
    assert len(suffix) == 35
