import pandas as pd

from src.parser import normalize_column_name, normalize_dataframe_columns, normalize_shift_name


def test_normalize_column_name_uses_common_names():
    assert normalize_column_name("No. of Heats") == "Heats_Produced"
    assert normalize_column_name("Metal Poured (Tonnes)") == "Metal_Poured_MT"
    assert normalize_column_name("Good Castings (Nos)") == "Castings_Produced"
    assert normalize_column_name("Total Downtime (min)") == "Downtime_Min"
    assert normalize_column_name("Safety Incidents") == "Safety_Incident"


def test_normalize_dataframe_columns_standardizes_headers():
    df = pd.DataFrame(
        [
            {
                "No. of Heats": 9,
                "Metal Poured (Tonnes)": 48.15,
                "Good Castings (Nos)": 1385,
                "Total Downtime (min)": 22,
                "Safety Incidents": "Nil",
            }
        ]
    )

    normalized = normalize_dataframe_columns(df)

    assert list(normalized.columns) == [
        "Heats_Produced",
        "Metal_Poured_MT",
        "Castings_Produced",
        "Downtime_Min",
        "Safety_Incident",
    ]


def test_normalize_shift_name_uses_canonical_shift_names():
    assert normalize_shift_name("Shift A") == "Shift_1"
    assert normalize_shift_name("Shift B") == "Shift_2"
    assert normalize_shift_name("Night Shift") == "Shift_3"
    assert normalize_shift_name("C") == "Shift_3"
