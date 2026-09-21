import re


column_mapping = {
    "Heats": "Heats_Produced",
    "No. of Heats": "Heats_Produced",
    "Total pouring": "Metal_Poured_MT",
    "Metal Poured (Tonnes)": "Metal_Poured_MT",
    "Pouring": "Metal_Poured_MT",
    "Castings": "Castings_Produced",
    "Good Castings (Nos)": "Castings_Produced",
    "Total pcs": "Castings_Produced",
    "Rejection": "Rejected_Castings",
    "Rejected Castings (Nos)": "Rejected_Castings",
    "3–4% rejection": "Rejection_Percentage",
    "3.03% rejection": "Rejection_Percentage",
    "30–35 pcs": "Rejected_Castings",
    "Rejection Reasons": "Rejection_Reason",
    "Blow hole": "Rejection_Reason",
    "Downtime": "Downtime_Min",
    "Total Downtime (min)": "Downtime_Min",
    "Crane": "Downtime_Reason",
    "Mold change": "Downtime_Reason",
    "Mould change over": "Downtime_Reason",
    "Power": "Downtime_Reason",
    "Mould shift": "Downtime_Reason",
    "Manpower": "Manpower_Present",
    "Operators Present": "Manpower_Present",
    "2 absent": "Manpower_Absent",
    "3 absent": "Manpower_Absent",
    "Safety near miss": "Safety_Incident",
    "Safety Incidents": "Safety_Incident",
    "Target 9": "Heat_Target",
    "Target achieved": "Heat_Target",
    "Charging crane issue": "Heat_Delay_Reason",
    "Power fluctuation": "Heat_Delay_Reason",
    "Pig Iron (kg)": "Pig_Iron_Kg",
    "Steel Scrap (kg)": "Steel_Scrap_Kg",
    "Returns / Runners (kg)": "Returns_Runners_Kg",
    "FeSi Added (kg)": "FeSi_Added_Kg",
    "Mg Alloy Added (kg)": "Mg_Alloy_Added_Kg",
    "Quality Hold Lots": "Quality_Hold",
    "Consumables normal": "Consumables_Status",
    "Handover done to A shift": "Handover",
    "heats": "Heats_Produced",
    "heats_target": "Heat_Target",
    "metal_poured_tonnes": "Metal_Poured_MT",
    "castings_total": "Castings_Produced",
    "operators_present": "Manpower_Present",
    "operators_absent": "Manpower_Absent",
    "rejection_reasons": "Rejection_Reason",
    "downtime_minutes": "Downtime_Min",
    "safety": "Safety_Incident",
}

shift_mapping = {
    "Shift A": "Shift_1",
    "Shift B": "Shift_2",
    "Shift C": "Shift_3",
    "Night Shift": "Shift_3",
    "A": "Shift_1",
    "B": "Shift_2",
    "C": "Shift_3",
}


def normalize_shift_name(shift_name):
    if shift_name is None:
        return None

    text = str(shift_name).strip()
    if not text:
        return text

    for raw_name, canonical_name in shift_mapping.items():
        if text.lower() == raw_name.lower():
            return canonical_name

    text_upper = text.upper()
    if text_upper in {"A", "SHIFT A"}:
        return "Shift_1"
    if text_upper in {"B", "SHIFT B"}:
        return "Shift_2"
    if text_upper in {"C", "SHIFT C", "NIGHT SHIFT"}:
        return "Shift_3"

    return text


def normalize_column_name(column_name):
    if column_name is None:
        return None

    text = str(column_name).strip().replace("–", "-").replace("—", "-")
    if not text:
        return ""

    if text in column_mapping:
        return column_mapping[text]

    compact_text = re.sub(r"[^a-z0-9]+", "", text.lower())

    for raw_name, canonical_name in column_mapping.items():
        if re.sub(r"[^a-z0-9]+", "", str(raw_name).lower()) == compact_text:
            return canonical_name

    return text


def normalize_dataframe_columns(df):
    if df is None:
        return df

    normalized = df.copy()
    new_columns = []
    seen = {}

    for column in normalized.columns:
        canonical_name = normalize_column_name(column)
        count = seen.get(canonical_name, 0)
        seen[canonical_name] = count + 1

        if count:
            canonical_name = f"{canonical_name}_{count}"

        new_columns.append(canonical_name)

    normalized.columns = new_columns
    return normalized


def extract_number(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return float(match.group(1).replace(",", ""))

    return None


def parse_report(text, shift=None, supervisor=None, source_type="Text"):

    text = text.replace("–", "-").replace("—", "-")

    # -------------------------
    # Shift
    # -------------------------

    if shift is None:

        match = re.search(
            r"Shift\s+([ABC])",
            text,
            re.IGNORECASE
        )

        if match:
            shift = match.group(1).upper()

        elif "Night Shift" in text:
            shift = "Night Shift"

        else:
            shift = "Unknown"

    shift = normalize_shift_name(shift)

    # -------------------------
    # Supervisor
    # -------------------------

    if supervisor is None:

        match = re.search(
            r"Regards,\s*(.+)",
            text,
            re.IGNORECASE
        )

        if match:
            supervisor = match.group(1).strip()

        else:
            supervisor = "Unknown"

    # -------------------------
    # Heats
    # -------------------------

    heats = extract_number(
        r"Heats\s*[-:]\s*(\d+)",
        text
    )

    target = extract_number(
        r"target\s*(\d+)",
        text
    )

    # -------------------------
    # Metal poured
    # -------------------------

    metal_poured = extract_number(
        r"(?:Total pouring|Pouring)\s*[-:]\s*([\d.]+)",
        text
    )

    # -------------------------
    # Castings
    # -------------------------

    castings = extract_number(
        r"(?:Castings|Total pcs)\s*[-:]\s*([\d,]+)",
        text
    )

    # -------------------------
    # Rejection range
    # -------------------------

    rejected_min = None
    rejected_max = None

    match = re.search(
        r"Rejection\s*[-:]\s*(?:around\s*)?(\d+)\s*-\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        rejected_min = int(match.group(1))
        rejected_max = int(match.group(2))

    # -------------------------
    # Rejection reasons
    # -------------------------

    reasons = []

    for reason in [
        "blow hole",
        "shrinkage",
        "dimensional"
    ]:

        if re.search(reason, text, re.IGNORECASE):

            reasons.append(reason)

    # -------------------------
    # Downtime
    # -------------------------

    downtime = 0

    matches = re.findall(
        r"(crane|mould change over|mould shift|power|other)[^\d]*(\d+)\s*min",
        text,
        re.IGNORECASE
    )

    for _, minutes in matches:

        downtime += int(minutes)

    # -------------------------
    # Manpower
    # -------------------------

    present = extract_number(
        r"(?:Manpower|Operators Present)\s*[-:]\s*(\d+)",
        text
    )

    absent = extract_number(
        r"(\d+)\s*absent",
        text
    )

    # -------------------------
    # Safety
    # -------------------------

    if re.search("near miss", text, re.IGNORECASE):

        safety = "Safety near miss"

    else:

        safety = "None stated"

    # -------------------------
    # Flags
    # -------------------------

    flags = []

    if re.search("blow hole", text, re.IGNORECASE):

        flags.append("Blow-hole issue")

    if re.search("crane", text, re.IGNORECASE):

        flags.append("Crane delay")

    if re.search(
        "power fluctuation|power",
        text,
        re.IGNORECASE
    ):

        flags.append("Power issue")

    if re.search("near miss", text, re.IGNORECASE):

        flags.append("Safety near miss")

    if re.search(
        "illegible|looks like",
        text,
        re.IGNORECASE
    ):

        flags.append("Uncertain note")

    if re.search(
        "Mg cylinder|need order",
        text,
        re.IGNORECASE
    ):

        flags.append("Mg cylinder order")

    if re.search(
        "quality hold|chemistry recheck",
        text,
        re.IGNORECASE
    ):

        flags.append("Quality hold")

    # -------------------------
    # Confidence
    # -------------------------

    confidence = "High"

    if re.search(
        r"approx|around|illegible|looks like|\d+\s*-\s*\d+",
        text,
        re.IGNORECASE
    ):

        confidence = "Medium/Low"

    # -------------------------
    # Final record
    # -------------------------

    return {

        "shift": shift,

        "supervisor": supervisor,

        "source_type": source_type,

        "Heats_Produced": heats,

        "Heat_Target": target,

        "Metal_Poured_MT": metal_poured,

        "Castings_Produced": castings,

        "Rejected_Castings": None,

        "Rejected_Min": rejected_min,

        "Rejected_Max": rejected_max,

        "Rejection_Reason":
            ", ".join(reasons)
            if reasons
            else "Not stated",

        "Downtime_Min":
            downtime,

        "Manpower_Present":
            present,

        "Manpower_Absent":
            absent,

        "Safety_Incident":
            safety,

        "legacy_heats": heats,

        "legacy_heats_target": target,

        "legacy_metal_poured_tonnes": metal_poured,

        "legacy_castings_total": castings,

        "legacy_rejected_min": rejected_min,

        "legacy_rejected_max": rejected_max,

        "legacy_rejection_reasons":
            ", ".join(reasons)
            if reasons
            else "Not stated",

        "legacy_downtime_minutes":
            downtime,

        "legacy_operators_present":
            present,

        "legacy_operators_absent":
            absent,

        "legacy_safety":
            safety,

        "attribution_status":
            "Pending production/inspection shift confirmation",

        "confidence":
            confidence,

        "review_status":
            "Review required"
            if confidence != "High"
            else "Ready for confirmation",

        "flags":
            "; ".join(flags)
            if flags
            else "None",

        "raw_input":
            text

    }
