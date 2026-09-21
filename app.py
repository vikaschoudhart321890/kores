import io

import pandas as pd
import streamlit as st

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

from src.parser import normalize_dataframe_columns, parse_report


def clean_ocr_text(raw_text: str) -> str:
    """Normalize OCR output for easier parsing."""
    text = raw_text or ""
    text = text.replace("\r", "\n")
    text = text.replace("–", "-").replace("—", "-")
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def extract_text_from_image(uploaded_file) -> str:
    """Read a report image and convert it into text with OCR."""
    if Image is None or ImageOps is None:
        raise RuntimeError("Pillow is not installed.")

    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed.")

    image_bytes = uploaded_file.read()
    image = Image.open(io.BytesIO(image_bytes))

    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")

    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    image = image.resize((image.width * 2, image.height * 2))

    text = pytesseract.image_to_string(image, config="--psm 6")
    return clean_ocr_text(text)


st.set_page_config(
    page_title="Kores Foundry Automation",
    layout="wide"
)


st.title(
    "Foundry Daily Production Report Normaliser"
)

st.caption(
    "Kores AI & Process Automation Prototype"
)


# ------------------------------------------------
# SAMPLE REPORTS
# ------------------------------------------------

shift_a = """
Shift A report

Heats - 8 target 9

Total pouring - 42.8 MT approx

Castings - 1,240 pcs

Rejection - around 3-4%
mostly blow holes in crank case
sand issue suspected

Downtime - 45 min crane + 20 min mould change over

Manpower - 22 present, 2 absent

One safety near miss at 11:40
worker slipped near ladle area
no injury

Detailed report will send by evening

Regards, Sunil Waghmare
"""


shift_c = """
Night Shift

Heats - 7
one heat cancelled due to power fluctuation

Pouring - ~37 T

Total pcs - 990 approx

Rejection - 30-35 pcs
blow hole still there

Downtime - power 40 min
mould shift 25 min
other approx 15 min

Manpower - 18 present, 3 absent

illegible note
Mg cylinder need order

Handover done to A shift

Bala
"""


# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------

st.sidebar.header("Prototype Controls")

option = st.sidebar.selectbox(
    "Select report view",
    ["All Reports", "Shift A", "Shift B", "Shift C"]
)

st.sidebar.subheader("Shift A - WhatsApp text")
shift_a_input = st.sidebar.text_area(
    "Paste Shift A report text",
    value=shift_a.strip(),
    height=220,
    help="Paste the Shift A WhatsApp message here to parse it."
)

st.sidebar.subheader("Shift B - Excel upload")
shift_b_file = st.sidebar.file_uploader(
    "Upload Shift B Excel file",
    type=["xlsx", "xls", "csv"],
    help="Upload the Shift B report in Excel or CSV format."
)

st.sidebar.subheader("Shift C - Photo upload")
shift_c_file = st.sidebar.file_uploader(
    "Upload Shift C photo",
    type=["png", "jpg", "jpeg", "bmp", "tif", "tiff"],
    help="Upload a photo of the Shift C report to extract text automatically."
)


# ------------------------------------------------
# PARSE REPORTS
# ------------------------------------------------

rows = []

if option in ["All Reports", "Shift A"] and shift_a_input.strip():
    rows.append(
        parse_report(
            shift_a_input,
            shift="A",
            supervisor="Sunil Waghmare",
            source_type="WhatsApp text"
        )
    )

if option in ["All Reports", "Shift B"] and shift_b_file is not None:
    try:
        if shift_b_file.name.lower().endswith(".csv"):
            df_excel = pd.read_csv(shift_b_file)
        else:
            df_excel = pd.read_excel(shift_b_file)

        if not df_excel.empty:
            for _, row in df_excel.iterrows():
                text = "\n".join(
                    str(value).strip()
                    for value in row.fillna("").tolist()
                    if str(value).strip()
                )

                if text:
                    rows.append(
                        parse_report(
                            text,
                            shift="B",
                            supervisor="Excel import",
                            source_type="Excel upload"
                        )
                    )

    except Exception as exc:
        st.sidebar.error(f"Shift B Excel parsing failed: {exc}")

if option in ["All Reports", "Shift C"] and shift_c_file is not None:
    try:
        with st.spinner("Extracting text from uploaded image..."):
            ocr_text = extract_text_from_image(shift_c_file)

        st.subheader("OCR Extracted Text")
        st.code(ocr_text[:4000])

        rows.append(
            parse_report(
                ocr_text,
                shift="C",
                supervisor="OCR extracted",
                source_type="Image OCR"
            )
        )

    except Exception as exc:
        st.sidebar.error(f"Shift C OCR failed: {exc}")

# Default sample rows only when the view is all and no uploads are provided
if option == "All Reports" and not rows:
    rows = [
        parse_report(
            shift_a,
            shift="A",
            supervisor="Sunil Waghmare",
            source_type="WhatsApp text"
        ),
        parse_report(
            shift_c,
            shift="C",
            supervisor="Bala",
            source_type="Handwritten transcription"
        )
    ]


# ------------------------------------------------
# DISPLAY
# ------------------------------------------------

if rows:

    df = normalize_dataframe_columns(pd.DataFrame(rows))

    if "Metal_Poured_MT" not in df.columns:
        df = df.rename(columns={
            "metal_poured_tonnes": "Metal_Poured_MT",
            "legacy_metal_poured_tonnes": "Metal_Poured_MT",
            "castings_total": "Castings_Produced",
            "legacy_castings_total": "Castings_Produced",
            "downtime_minutes": "Downtime_Min",
            "legacy_downtime_minutes": "Downtime_Min",
            "heats": "Heats_Produced",
            "legacy_heats": "Heats_Produced",
            "rejection_reasons": "Rejection_Reason",
            "legacy_rejection_reasons": "Rejection_Reason",
            "safety": "Safety_Incident",
            "legacy_safety": "Safety_Incident",
            "operators_present": "Manpower_Present",
            "operators_absent": "Manpower_Absent",
            "legacy_operators_present": "Manpower_Present",
            "legacy_operators_absent": "Manpower_Absent",
        })

    st.subheader("Review Queue")

    st.dataframe(
        df,
        width="stretch",
        hide_index=True
    )


    # --------------------------------------------
    # SUMMARY
    # --------------------------------------------

    st.subheader("10 AM Exception Summary")

    col1, col2, col3, col4 = st.columns(4)


    total_shifts = len(df)


    total_tonnes = (
        pd.to_numeric(
            df["Metal_Poured_MT"] if "Metal_Poured_MT" in df.columns else df["metal_poured_tonnes"],
            errors="coerce"
        )
        .sum()
    )


    total_castings = (
        pd.to_numeric(
            df["Castings_Produced"] if "Castings_Produced" in df.columns else df["castings_total"],
            errors="coerce"
        )
        .sum()
    )


    total_downtime = (
        pd.to_numeric(
            df["Downtime_Min"] if "Downtime_Min" in df.columns else df["downtime_minutes"],
            errors="coerce"
        )
        .sum()
    )


    col1.metric(
        "Shifts",
        total_shifts
    )


    col2.metric(
        "Metal Poured",
        f"{total_tonnes:.1f} T"
    )


    col3.metric(
        "Castings",
        f"{total_castings:,.0f}"
    )


    col4.metric(
        "Downtime",
        f"{total_downtime:.0f} min"
    )


    # --------------------------------------------
    # EXCEPTIONS
    # --------------------------------------------

    st.subheader("Exceptions")


    exceptions = []


    for value in df["flags"]:

        if value != "None":

            exceptions.extend(
                value.split(";")
            )


    if exceptions:

        exception_df = pd.DataFrame(
            {
                "Exception":
                    sorted(set(exceptions))
            }
        )

        st.dataframe(
            exception_df,
            width="stretch",
            hide_index=True
        )


    # --------------------------------------------
    # ATTRIBUTION CONTROL
    # --------------------------------------------

    st.subheader(
        "Rejection Attribution Control"
    )


    st.info(
        "Rejection responsibility is not automatically assigned. "
        "Production shift and inspection shift must be confirmed."
    )


    attribution_columns = [
        "shift",
        "Rejected_Min" if "Rejected_Min" in df.columns else "rejected_min",
        "Rejected_Max" if "Rejected_Max" in df.columns else "rejected_max",
        "Rejection_Reason" if "Rejection_Reason" in df.columns else "rejection_reasons",
        "attribution_status",
        "confidence"
    ]

    st.dataframe(
        df[attribution_columns],
        width="stretch",
        hide_index=True
    )


    # --------------------------------------------
    # DOWNLOAD
    # --------------------------------------------

    csv = df.to_csv(
        index=False
    )


    st.download_button(
        "Download Consolidated CSV",
        csv,
        "kores_daily_report.csv",
        "text/csv"
    )