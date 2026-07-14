import json
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent

st.set_page_config(layout="wide", page_title="Provost Command Center", page_icon="🛡️")

st.markdown(
    """
    <style>
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      [data-testid="stToolbar"] {visibility: hidden;}
      [data-testid="stDecoration"] {display: none;}

      .main-header {
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 14px;
        background: linear-gradient(120deg, rgba(14, 20, 33, 0.95), rgba(18, 46, 61, 0.85));
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
      }

      .main-header h1 {
        margin: 0;
        color: #f5f8ff;
        letter-spacing: 0.4px;
      }

      .main-header p {
        margin: 0.35rem 0 0;
        color: #a8b3c7;
      }

      .metric-card {
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        padding: 0.95rem 1rem;
        background: linear-gradient(145deg, rgba(16, 22, 34, 0.92), rgba(9, 31, 43, 0.88));
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
      }

      .metric-label {
        color: #9eb2c5;
        font-size: 0.88rem;
        letter-spacing: 0.3px;
      }

      .metric-value {
        color: #ebf2ff;
        font-size: 1.7rem;
        font-weight: 700;
        margin-top: 0.2rem;
      }

      .metric-value.alert {
        color: #ff5c5c;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_json_loads(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def parse_intent(request_body: Any) -> tuple[str, Any, Any, float]:
    parsed = safe_json_loads(request_body)
    symbol = "N/A"
    qty: Any = "N/A"
    side: Any = "N/A"
    notional_value = 0.0

    if not parsed:
        return symbol, qty, side, notional_value

    method = parsed.get("method")
    params = parsed.get("params", {}) if isinstance(parsed.get("params"), dict) else {}

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {}) if isinstance(params.get("arguments"), dict) else {}

        if tool_name in {"create_order", "place_stock_order"}:
            symbol = arguments.get("symbol", "N/A")
            qty = arguments.get("qty", "N/A")
            side = arguments.get("side", "N/A")
            qty_num = to_float(qty)
            # Demo notional estimation for governance analytics.
            notional_value = qty_num * 150 if qty_num > 0 else 0.0

    return symbol, qty, side, notional_value


def parse_http_request(request_field: Any) -> tuple[str, str]:
    """Parse 'DELETE /v2/positions HTTP/1.1' into method and path."""
    if not isinstance(request_field, str) or not request_field.strip():
        return "N/A", "N/A"
    parts = request_field.split(" ")
    if len(parts) >= 2:
        return parts[0], parts[1]  # method, path
    return "N/A", "N/A"


def normalize_json_for_code(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "{}"

    stripped = raw.strip()

    parsed = safe_json_loads(stripped)
    if parsed is not None:
        return json.dumps(parsed, indent=2, ensure_ascii=False)

    # Some responses are SSE envelopes; pull first JSON payload after `data:`.
    if "data:" in stripped:
        for line in stripped.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line.replace("data:", "", 1).strip()
                payload_parsed = safe_json_loads(payload)
                if payload_parsed is not None:
                    return json.dumps(payload_parsed, indent=2, ensure_ascii=False)

    return stripped


@st.cache_data(ttl=5)
def load_data() -> pd.DataFrame:
    data_root = APP_DIR / "data" / "logs"
    files = glob(str(data_root / "**" / "*.json"), recursive=True) + glob(
        str(data_root / "**" / "*.jsonl"), recursive=True
    )

    records: list[dict[str, Any]] = []

    for file_path in files:
        file_type = "access" if "/access/" in file_path else "error" if "/error/" in file_path else "unknown"

        try:
            with Path(file_path).open("r", encoding="utf-8") as handle:
                for line in handle:
                    raw = line.strip()
                    if not raw:
                        continue

                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(payload, dict):
                        continue

                    symbol, qty, side, notional_value = parse_intent(payload.get("request_body", ""))
                    http_method, http_path = parse_http_request(payload.get("request", ""))

                    records.append(
                        {
                            "source_file": file_path,
                            "log_schema": file_type,
                            "date": payload.get("date", "N/A"),
                            "time_local": payload.get("time_local", "N/A"),
                            "remote_addr": payload.get("remote_addr", "N/A"),
                            "request": payload.get("request", "N/A"),
                            "status": str(payload.get("status", "N/A")),
                            "body_bytes_sent": payload.get("body_bytes_sent", "N/A"),
                            "request_time": payload.get("request_time", "N/A"),
                            "upstream_response_time": payload.get("upstream_response_time", "N/A"),
                            "provost_request_id": payload.get("provost_request_id", "N/A"),
                            "provost_user": payload.get("provost_user", "N/A") or "N/A",
                            "provost_machine": payload.get("provost_machine", "N/A") or "N/A",
                            "request_body": payload.get("request_body", "N/A"),
                            "resp_body": payload.get("resp_body", "N/A"),
                            "error_code": payload.get("error_code", "N/A"),
                            "error_detail": payload.get("error_detail", "N/A") or "N/A",
                            "Region": payload.get("Region", "N/A"),
                            "Instance_ID": payload.get("Instance_ID", "N/A"),
                            "symbol": symbol,
                            "qty": qty,
                            "side": side,
                            "notional_value": notional_value,
                            "http_method": http_method,
                            "http_path": http_path,
                            "is_http_block": (http_method != "POST" or http_path != "/mcp"),
                        }
                    )
        except OSError:
            continue

    if not records:
        return pd.DataFrame(
            columns=[
                "time_local",
                "status",
                "provost_user",
                "symbol",
                "qty",
                "error_code",
                "error_detail",
                "provost_request_id",
                "request_body",
                "resp_body",
                "Region",
                "Instance_ID",
                "notional_value",
                "http_method",
                "http_path",
                "is_http_block",
            ]
        )

    df = pd.DataFrame(records)

    # Enforce merged schema defaults for access/error heterogeneity.
    for col in [
        "body_bytes_sent",
        "request_time",
        "upstream_response_time",
        "error_code",
        "error_detail",
        "symbol",
        "qty",
        "side",
        "request_body",
        "resp_body",
    ]:
        if col not in df.columns:
            df[col] = "N/A"
        df[col] = df[col].fillna("N/A")

    df["notional_value"] = pd.to_numeric(df["notional_value"], errors="coerce").fillna(0.0)

    parsed_time = pd.to_datetime(
        df["time_local"], format="%d/%b/%Y:%H:%M:%S %z", errors="coerce", utc=True
    )
    fallback_time = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["time_dt"] = parsed_time.fillna(fallback_time)

    df = df.sort_values("time_dt", ascending=True, na_position="last").reset_index(drop=True)

    return df


def metric_card(label: str, value: str, alert: bool = False) -> None:
    alert_class = "alert" if alert else ""
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value {alert_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_plotly(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=45, b=20),
    )
    return fig


df = load_data()

st.markdown(
    """
    <div class="main-header">
      <h1>Provost Command Center</h1>
      <p>Executive observability for AI governance, enforcement, and compliance posture.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No logs were found under ./data/logs/. Confirm data sync and file paths.")
    st.stop()

valid_times = df["time_dt"].dropna()
if valid_times.empty:
    st.warning("No valid timestamps were found in the log dataset.")
    st.stop()

min_time = valid_times.min()
max_time = valid_times.max()

if getattr(min_time, "tzinfo", None) is not None:
    min_time = min_time.tz_convert("UTC").tz_localize(None)
if getattr(max_time, "tzinfo", None) is not None:
    max_time = max_time.tz_convert("UTC").tz_localize(None)

with st.expander("⏱️ Global Time Window (UTC)", expanded=False):
    _tc1, _tc2, _tc3, _tc4 = st.columns(4)
    with _tc1:
        start_date = st.date_input(
            "Start date",
            value=min_time.date(),
            min_value=min_time.date(),
            max_value=max_time.date(),
            key="global_start_date",
        )
    with _tc2:
        start_time = st.time_input(
            "Start time",
            value=min_time.time().replace(microsecond=0),
            key="global_start_time",
        )
    with _tc3:
        end_date = st.date_input(
            "End date",
            value=max_time.date(),
            min_value=min_time.date(),
            max_value=max_time.date(),
            key="global_end_date",
        )
    with _tc4:
        end_time = st.time_input(
            "End time",
            value=max_time.time().replace(microsecond=0),
            key="global_end_time",
        )

start_dt_utc = pd.Timestamp(datetime.combine(start_date, start_time), tz="UTC")
end_dt_utc = pd.Timestamp(datetime.combine(end_date, end_time), tz="UTC")

if end_dt_utc < start_dt_utc:
    st.error("Invalid time window: End date/time must be greater than or equal to start date/time.")
    st.stop()

filtered_df = df[(df["time_dt"] >= start_dt_utc) & (df["time_dt"] <= end_dt_utc)].copy()

if filtered_df.empty:
    st.info("No records found for the selected date/time range. Expand the time window to see results.")
    st.stop()

tab1, tab2, tab3 = st.tabs(
    ["🛡️ Governance & Security", "📈 Operational Throughput", "🔎 Forensic Audit"]
)

with tab1:
    violations_403 = int((filtered_df["status"] == "403").sum())
    threats_401 = int((filtered_df["status"] == "401").sum())
    var_protected = float(filtered_df.loc[filtered_df["status"] == "403", "notional_value"].sum())

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        metric_card("Policy Violations Prevented", f"{violations_403:,}", alert=violations_403 > 0)
    with col_b:
        metric_card("Security Threats Blocked", f"{threats_401:,}", alert=threats_401 > 0)
    with col_c:
        metric_card("Value at Risk (VaR) Protected", f"${var_protected:,.0f}", alert=var_protected > 0)

    blocked_df = filtered_df[filtered_df["status"].isin(["401", "403", "429"])].copy()
    if not blocked_df.empty:
        blocked_df["time_bucket"] = blocked_df["time_dt"].dt.floor("h")
        blocked_series = (
            blocked_df.groupby(["time_bucket", "status"], dropna=False).size().reset_index(name="count")
        )
        blocked_series["time_bucket"] = blocked_series["time_bucket"].astype(str)

        bar_fig = px.bar(
            blocked_series,
            x="time_bucket",
            y="count",
            color="status",
            barmode="group",
            title="Blocked Requests Over Time (401 / 403 / 429)",
            labels={"time_bucket": "Time", "count": "Blocked Requests", "status": "Status"},
        )
        bar_fig = style_plotly(bar_fig)
    else:
        bar_fig = style_plotly(px.bar(title="Blocked Requests Over Time (401 / 403 / 429)"))

    st.plotly_chart(bar_fig, use_container_width=True)

    reasons_df = filtered_df[(filtered_df["status"] == "403") & (filtered_df["error_detail"] != "N/A")].copy()
    reasons_df = reasons_df[reasons_df["error_detail"].astype(str).str.strip() != ""]

    donut_col, table_col = st.columns([1, 1])

    if not reasons_df.empty:
        donut_data = reasons_df.groupby("error_detail", dropna=False).size().reset_index(name="count")
        donut_fig = px.pie(
            donut_data,
            names="error_detail",
            values="count",
            hole=0.58,
            title="403 Guardrail Interventions by Reason",
        )
        donut_fig = style_plotly(donut_fig)
        donut_fig.update_layout(showlegend=False)
        reason_table = donut_data.sort_values("count", ascending=False).reset_index(drop=True)
    else:
        donut_fig = style_plotly(px.pie(title="403 Guardrail Interventions by Reason"))
        reason_table = None

    with donut_col:
        st.plotly_chart(donut_fig, use_container_width=True)
    with table_col:
        st.markdown("**Guardrail Intervention Reasons**")
        if reason_table is not None and not reason_table.empty:
            st.dataframe(
                reason_table.rename(columns={"error_detail": "Reason", "count": "Count"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No 403 guardrail reasons found in selected time window.")

    # Filter for Hop 2 HTTP Blocks
    http_blocks_df = filtered_df[filtered_df["is_http_block"]]

    if not http_blocks_df.empty:
        st.subheader("🚫 Forbidden HTTP Endpoint Blocks (Hop 2)")
        st.dataframe(
            http_blocks_df[["time_local", "http_method", "http_path", "error_detail", "status"]],
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    total_actions = len(filtered_df)
    successful_count = int(filtered_df["status"].isin(["200", "202"]).sum())

    tcol1, tcol2 = st.columns(2)
    with tcol1:
        metric_card("Total AI Actions Governed", f"{total_actions:,}")
    with tcol2:
        metric_card("Successful Executions", f"{successful_count:,}")

    success_df = filtered_df[filtered_df["status"].isin(["200", "202"])].copy()

    if not success_df.empty:
        success_df["time_bucket"] = success_df["time_dt"].dt.floor("h")
        success_series = success_df.groupby("time_bucket", dropna=False).size().reset_index(name="count")
        success_series["time_bucket"] = success_series["time_bucket"].astype(str)

        area_fig = px.area(
            success_series,
            x="time_bucket",
            y="count",
            title="Successful Request Volume Over Time",
            labels={"time_bucket": "Time", "count": "Successful Requests"},
        )
        area_fig.update_traces(line_color="#00FF00", fillcolor="rgba(0,255,0,0.25)")
        area_fig = style_plotly(area_fig)
        st.plotly_chart(area_fig, use_container_width=True)

        symbol_df = success_df[success_df["symbol"] != "N/A"].copy()
        if not symbol_df.empty:
            symbol_rank = (
                symbol_df.groupby("symbol", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)
            )
            symbol_fig = px.bar(
                symbol_rank,
                x="symbol",
                y="count",
                title="Most Frequently Traded Symbols (Successful Logs)",
                labels={"symbol": "Symbol", "count": "Trade Count"},
            )
            symbol_fig = style_plotly(symbol_fig)
            st.plotly_chart(symbol_fig, use_container_width=True)
        else:
            st.info("No successful symbol-trading records were detected in parsed intents.")
    else:
        st.info("No successful (200/202) records available for throughput analytics.")

with tab3:
    status_options = sorted(filtered_df["status"].dropna().astype(str).unique().tolist())
    user_options = sorted(filtered_df["provost_user"].fillna("N/A").astype(str).unique().tolist())

    _fc1, _fc2 = st.columns(2)
    with _fc1:
        selected_status = st.multiselect(
            "Filter by status code",
            options=status_options,
            default=status_options,
        )
    with _fc2:
        selected_users = st.multiselect(
            "Filter by provost_user",
            options=user_options,
            default=user_options,
        )

    forensic_df = filtered_df[
        filtered_df["status"].isin(selected_status) & filtered_df["provost_user"].isin(selected_users)
    ].copy()

    ledger_cols = ["time_local", "status", "provost_user", "symbol", "qty", "error_code", "error_detail"]
    st.dataframe(forensic_df[ledger_cols], use_container_width=True, height=420)

    request_ids = [rid for rid in forensic_df["provost_request_id"].astype(str).unique().tolist() if rid != "N/A"]
    selected_id = st.selectbox("Select provost_request_id", options=["N/A"] + request_ids)

    if selected_id != "N/A":
        selected_rows = forensic_df[forensic_df["provost_request_id"].astype(str) == selected_id]
        if not selected_rows.empty:
            selected_row = selected_rows.iloc[-1]

            region = selected_row.get("Region", "N/A")
            instance_id = selected_row.get("Instance_ID", "N/A")
            st.markdown(f"Infrastructure provenance: **Instance_ID:** {instance_id} | **Region:** {region}")

            left, right = st.columns(2)
            with left:
                st.markdown("**AI Intent (request_body)**")
                st.code(normalize_json_for_code(selected_row.get("request_body", "")), language="json")
            with right:
                st.markdown("**Provost Enforcement (resp_body)**")
                st.code(normalize_json_for_code(selected_row.get("resp_body", "")), language="json")
        else:
            st.info("No record found for the selected request ID under current filters.")
