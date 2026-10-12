import pandas as pd

from threathunt.c2_classifier import FEATURE_COLUMNS, build_features, train


def _synthetic_dataset():
    rows = []
    for label, ua, url in [
        ("c2", "Mozilla/5.0 (compatible; MSIE 10.0)", "/css/1vaHF9847ooFJg/qcOiyus"),
        ("malware", "SunShineMoonLight", "/panel/gate.php"),
        ("pua", "rclone/v1.67.0", "/api/upload"),
        ("rmm", "AnyDesk/8.0.10", "/connect"),
    ]:
        for i in range(6):
            rows.append({
                "http_user_agent": ua,
                "url": f"{url}?id={i}" if i % 2 == 0 else url,
                "http_method": "GET" if i % 2 == 0 else "POST",
                "status": 200,
                "label": label,
            })
    return pd.DataFrame(rows)


def test_build_features_has_expected_columns():
    df = _synthetic_dataset()
    features = build_features(df)
    assert list(features.columns) == FEATURE_COLUMNS
    assert len(features) == len(df)


def test_train_produces_a_model_and_report():
    df = _synthetic_dataset()
    model, X_test, y_test, report = train(df, test_size=0.3, random_state=0)
    assert len(X_test) == len(y_test)
    predictions = model.predict(X_test)
    assert set(predictions) <= set(df["label"].unique())
    assert "precision" in report
