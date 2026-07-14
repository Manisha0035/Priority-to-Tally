"""
po_dashboard.py — Priority ERP → Tally Middleware
──────────────────────────────────────────────────
Run with:
    pip install streamlit requests pandas
    streamlit run po_dashboard.py
"""

import base64
import json as _json
import os
import re
import time
from datetime import datetime, timedelta
from xml.sax.saxutils import escape, quoteattr

import pandas as pd
import requests
import streamlit as st

def _xml_text(value) -> str:
    return escape("" if value is None else str(value), {'"': "&quot;", "'": "&apos;"})

def _xml_attr(value) -> str:
    return quoteattr("" if value is None else str(value))

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Priority → Tally Middleware",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0d1117; color: #c9d1d9; }

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
    border: 1px solid #21262d; border-radius: 14px;
    padding: 24px 32px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 20px;
}
.app-logo { font-size: 36px; line-height: 1; }
.app-title { font-size: 22px; font-weight: 700; color: #f0f6fc; letter-spacing: -0.3px; margin: 0; }
.app-subtitle { font-size: 13px; color: #8b949e; margin: 3px 0 0 0; }
.app-badge {
    margin-left: auto; background: #21262d; border: 1px solid #30363d;
    border-radius: 20px; padding: 4px 14px; font-size: 12px; color: #58a6ff;
    font-weight: 600; white-space: nowrap;
}

/* ── KPI Cards Grid ── */
.kpi-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 12px; margin-bottom: 24px; }
.kpi { border-radius: 12px; padding: 16px 20px; border: 1px solid; }
.kpi-total     { background: #161b22; border-color: #30363d; }
.kpi-auth      { background: #0d1b36; border-color: #1f4068; }
.kpi-final     { background: #0d2618; border-color: #1a4731; }
.kpi-confirmed { background: #1b162e; border-color: #44337a; }
.kpi-vinvoice  { background: #0d1a2e; border-color: #1a3a5c; }
.kpi-closed    { background: #2d1515; border-color: #6e2e2e; }
.kpi-label { font-size: 11px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 8px; }
.kpi-total .kpi-label     { color: #8b949e; }
.kpi-auth .kpi-label      { color: #79c0ff; }
.kpi-final .kpi-label     { color: #56d364; }
.kpi-confirmed .kpi-label { color: #b779ff; }
.kpi-invoice .kpi-label   { color: #e3b341; }
.kpi-closed .kpi-label    { color: #f85149; }
.kpi-count { font-family: 'JetBrains Mono', monospace; font-size: 34px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.kpi-total .kpi-count     { color: #f0f6fc; }
.kpi-auth .kpi-count      { color: #58a6ff; }
.kpi-final .kpi-count     { color: #3fb950; }
.kpi-confirmed .kpi-count { color: #af40ff; }
.kpi-invoice .kpi-count   { color: #e3b341; }
.kpi-closed .kpi-count    { color: #f85149; }
.kpi-amount { font-size: 12px; font-weight: 500; color: #8b949e; }

/* ── Section headings ── */
.sec { font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600;
       color: #8b949e; letter-spacing: 1.5px; text-transform: uppercase;
       margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #21262d; }

/* ── Alerts ── */
.alert { border-radius: 10px; padding: 14px 18px; font-size: 13px; margin-bottom: 14px; line-height: 1.6; }
.alert-info    { background: #0d1b36; border: 1px solid #1f4068; color: #79c0ff; }
.alert-success { background: #0d2618; border: 1px solid #1a4731; color: #56d364; }
.alert-warn    { background: #271d0a; border: 1px solid #5a3e12; color: #e3b341; }
.alert-error   { background: #2d1515; border: 1px solid #6e2e2e; color: #f85149; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #161b22; border-radius: 10px; padding: 4px; gap: 4px; border: 1px solid #21262d;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: #8b949e; border-radius: 7px;
    font-family: 'Inter', sans-serif; font-weight: 600; font-size: 13px; padding: 7px 18px;
}
.stTabs [aria-selected="true"] { background: #1f4068 !important; color: #f0f6fc !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #161b22 !important;
    border-right: 1px solid #21262d !important;
}
section[data-testid="stSidebar"] h2 {
    color: #f0f6fc !important; font-size: 15px !important;
    font-family: 'JetBrains Mono', monospace;
}
section[data-testid="stSidebar"] .stRadio > label {
    color: #8b949e !important; font-size: 11px !important;
    font-weight: 700 !important; letter-spacing: 1px !important; text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR NAVIGATION SWITCHER ──────────────────────────────────────────────

# Module groups — order matches the desired sidebar layout
_NAV_GROUPS = {
    "📦 Purchase Module": [
        "Purchase Orders Module",
        "Goods Receiving Vouchers",
        "Multi GRV Invoice Module",
    ],
    "🛒 Sales Module": [
        "Sales Orders Module",
        "Sales Invoices Module",
        "OTC Sales Invoices Module",
        "Multi Shipment Invoice Module",
        "Shipping Documents Module",
    ],
    "📒 Finance Module": [
        "Entry Journal Module",
    ],
}
_FLAT_MODULE = "Bulk Sync Module"

# Initialise session state
if "active_module" not in st.session_state:
    st.session_state["active_module"] = "Purchase Orders Module"
if "nav_open_group" not in st.session_state:
    # Default: open whichever group contains the active module
    _default_grp = next(
        (g for g, mods in _NAV_GROUPS.items() if st.session_state["active_module"] in mods),
        list(_NAV_GROUPS.keys())[0],
    )
    st.session_state["nav_open_group"] = _default_grp

with st.sidebar:
    st.markdown("## 🛠 Middleware Engines")

    # ── Sidebar styles ──────────────────────────────────────────────────────────
    # HOW THIS WORKS
    # ──────────────────────────────────────────────────────────────────────────
    # Streamlit does NOT set a `title` attribute from the button label text —
    # `title` only appears when you pass help= to st.button(). So the old
    # button[title*="..."] selectors matched nothing and every button looked
    # identical.
    #
    # What actually works in the DOM:
    #   • Every sidebar button renders as:
    #       div.stButton[data-testid="stButton"]
    #         └─ button[data-testid="stBaseButton-secondary"][kind="secondary"]
    #   • There is NO stable per-button DOM attribute we can use to tell a
    #     group-header button apart from a child-module button.
    #
    # The fix: inject a zero-height HTML sentinel <div> immediately before each
    # group of child buttons using st.markdown(). CSS can then target buttons
    # that follow a sentinel via the adjacent-sibling combinator (+) or a
    # descendant match on a wrapping class.
    #
    # We use two sentinel classes:
    #   .nav-group-header  → injected just before every parent-group button
    #   .nav-children      → injected just before the first child of an open group
    #
    # Because Streamlit wraps every st.markdown() + st.button() in a shared
    # stVerticalBlock, the DOM looks like:
    #
    #   stVerticalBlock
    #     div.nav-group-header   ← sentinel
    #     div.stButton           ← group header button  (sibling after sentinel)
    #     div.nav-children       ← sentinel (only when group is open)
    #     div.stButton           ← child 1  (sibling after .nav-children)
    #     div.stButton           ← child 2  (general sibling ~)
    #     …
    #     div.nav-group-header   ← next group sentinel
    #     …
    #
    # We use ~ (general sibling) to paint ALL child buttons between one
    # .nav-children sentinel and the next .nav-group-header sentinel, and
    # we cancel the child style when a .nav-group-header re-appears.
    st.markdown("""
    <style>
    /* ── sentinel divs ── */
    div[data-testid="stSidebar"] .nav-group-header,
    div[data-testid="stSidebar"] .nav-children { display: none; }

    /* ══════════════════════════════════════════════════════
       BASE RESET — all sidebar buttons left-aligned
    ══════════════════════════════════════════════════════ */
    div[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
        text-align: left !important;
        justify-content: flex-start !important;
    }

    /* ══════════════════════════════════════════════════════
       PARENT GROUP HEADERS — bold pill with solid bg
    ══════════════════════════════════════════════════════ */
    div[data-testid="stSidebar"] .nav-group-header + div[data-testid="stButton"] button {
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.07em !important;
        text-transform: uppercase !important;
        color: #ffffff !important;
        padding: 0.55rem 1rem !important;
        border-radius: 7px !important;
        background: rgba(55, 110, 170, 0.55) !important;
        border: 1px solid rgba(99, 179, 237, 0.50) !important;
        transition: background 0.15s, border-color 0.15s !important;
        min-height: 2.4rem !important;
    }
    div[data-testid="stSidebar"] .nav-group-header + div[data-testid="stButton"] button:hover {
        background: rgba(55, 110, 170, 0.80) !important;
        border-color: rgba(99, 179, 237, 0.85) !important;
    }

    /* ══════════════════════════════════════════════════════
       CHILD MODULE BUTTONS — slim, indented, muted
    ══════════════════════════════════════════════════════ */
    div[data-testid="stSidebar"] .nav-children ~ div[data-testid="stButton"] button {
        font-size: 0.76rem !important;
        font-weight: 400 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        color: rgba(180, 205, 230, 0.75) !important;
        padding: 0.25rem 0.6rem 0.25rem 1.5rem !important;
        border-radius: 5px !important;
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        min-height: 1.9rem !important;
        transition: background 0.12s, color 0.12s !important;
    }
    div[data-testid="stSidebar"] .nav-children ~ div[data-testid="stButton"] button:hover {
        background: rgba(99,179,237,0.10) !important;
        border-color: rgba(99,179,237,0.25) !important;
        color: #e6f0ff !important;
    }
    div[data-testid="stSidebar"] .nav-children ~ div[data-testid="stButton"] button:focus-visible {
        background: rgba(88,166,255,0.15) !important;
        border-left: 3px solid #58a6ff !important;
        padding-left: calc(1.5rem - 3px) !important;
        color: #cae8ff !important;
        font-weight: 600 !important;
        outline: none !important;
    }

    /* ── reset back to parent style after next .nav-group-header ── */
    div[data-testid="stSidebar"] .nav-children ~ .nav-group-header ~ div[data-testid="stButton"] button {
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.07em !important;
        text-transform: uppercase !important;
        color: #ffffff !important;
        padding: 0.55rem 1rem !important;
        border-radius: 7px !important;
        background: rgba(55, 110, 170, 0.55) !important;
        border: 1px solid rgba(99, 179, 237, 0.50) !important;
        min-height: 2.4rem !important;
    }
    div[data-testid="stSidebar"] .nav-children ~ .nav-group-header ~ div[data-testid="stButton"] button:hover {
        background: rgba(55, 110, 170, 0.80) !important;
        border-color: rgba(99, 179, 237, 0.85) !important;
    }

    /* ── re-apply child style after second .nav-children ── */
    div[data-testid="stSidebar"] .nav-children ~ .nav-group-header ~ .nav-children ~ div[data-testid="stButton"] button {
        font-size: 0.76rem !important;
        font-weight: 400 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        color: rgba(180, 205, 230, 0.75) !important;
        padding: 0.25rem 0.6rem 0.25rem 1.5rem !important;
        border-radius: 5px !important;
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        min-height: 1.9rem !important;
    }
    div[data-testid="stSidebar"] .nav-children ~ .nav-group-header ~ .nav-children ~ div[data-testid="stButton"] button:hover {
        background: rgba(99,179,237,0.10) !important;
        border-color: rgba(99,179,237,0.25) !important;
        color: #e6f0ff !important;
    }

    /* ── Clear Cache — subtle outlined button ── */
    div[data-testid="stSidebar"] .nav-clear-cache + div[data-testid="stButton"] button {
        font-size: 0.74rem !important;
        font-weight: 400 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        color: rgba(160, 185, 210, 0.55) !important;
        background: transparent !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 6px !important;
        padding: 0.35rem 0.75rem !important;
    }
    div[data-testid="stSidebar"] .nav-clear-cache + div[data-testid="stButton"] button:hover {
        color: rgba(220, 235, 250, 0.80) !important;
        border-color: rgba(255,255,255,0.25) !important;
        background: rgba(255,255,255,0.04) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Navigation rendering ────────────────────────────────────────────────────
    for _group_label, _group_modules in _NAV_GROUPS.items():
        _is_open = st.session_state["nav_open_group"] == _group_label
        _arrow = "▾" if _is_open else "▸"

        # Sentinel: marks the NEXT sibling as a group-header button
        st.markdown('<div class="nav-group-header"></div>', unsafe_allow_html=True)

        if st.button(f"{_arrow} {_group_label}", key=f"nav_grp_{_group_label}", use_container_width=True):
            if _is_open:
                st.session_state["nav_open_group"] = None
            else:
                st.session_state["nav_open_group"] = _group_label
            st.rerun()

        if _is_open:
            # Sentinel: marks all following siblings (until next group header) as children
            st.markdown('<div class="nav-children"></div>', unsafe_allow_html=True)
            for _mod in _group_modules:
                _is_active = st.session_state["active_module"] == _mod
                _label = f"{'● ' if _is_active else '  '}{_mod}"
                if st.button(_label, key=f"nav_mod_{_mod}", use_container_width=True):
                    st.session_state["active_module"] = _mod
                    st.session_state["nav_open_group"] = _group_label
                    st.rerun()

    # Flat top-level item: Bulk Sync — same header style
    st.markdown('<div class="nav-group-header"></div>', unsafe_allow_html=True)
    _bulk_active = st.session_state["active_module"] == _FLAT_MODULE
    _bulk_label = f"{'● ' if _bulk_active else ''}⚡ Bulk Pushing"
    if st.button(_bulk_label, key="nav_mod_bulk", use_container_width=True):
        st.session_state["active_module"] = _FLAT_MODULE
        st.session_state["nav_open_group"] = None
        st.rerun()

    active_module = st.session_state["active_module"]

    # ── Nav loading indicator ───────────────────────────────────────────────────
    # On click: dims the button + shows a spinner inline via CSS class.
    # Streamlit's re-render rebuilds the sidebar DOM, removing it automatically.
    st.markdown("""
    <style>
    @keyframes nav-spin { to { transform: rotate(360deg); } }
    div[data-testid="stSidebar"] button.nav-loading {
        opacity: 0.50 !important;
        cursor: wait !important;
        pointer-events: none !important;
    }
    div[data-testid="stSidebar"] button.nav-loading::before {
        content: "" !important;
        display: inline-block !important;
        width: 0.72em !important;
        height: 0.72em !important;
        border: 2px solid rgba(180,210,255,0.30) !important;
        border-top-color: #7ab8f5 !important;
        border-radius: 50% !important;
        animation: nav-spin 0.65s linear infinite !important;
        margin-right: 0.45em !important;
        vertical-align: middle !important;
        flex-shrink: 0 !important;
    }
    </style>
    <script>
    (function () {
        function attach() {
            var sidebar = document.querySelector('[data-testid="stSidebar"]');
            if (!sidebar) { setTimeout(attach, 150); return; }
            if (sidebar._navLoaderAttached) return;
            sidebar._navLoaderAttached = true;
            sidebar.addEventListener('click', function (e) {
                var btn = e.target.closest('button[data-testid="stBaseButton-secondary"]');
                if (!btn) return;
                if ((btn.innerText || '').indexOf('Clear Cache') !== -1) return;
                btn.classList.add('nav-loading');
            });
        }
        new MutationObserver(function () { attach(); })
            .observe(document.body, { childList: true, subtree: false });
        attach();
    })();
    </script>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="nav-clear-cache"></div>', unsafe_allow_html=True)
    if st.button("⟳ Clear Cache & Re-Sync", use_container_width=True):
        st.cache_data.clear()
        # Also wipe session-state override sets so "Already in Tally" markers
        # are re-evaluated fresh from Tally — not from stale in-memory sets
        for _k in [
            "vinv_tally_nos_override", "po_tally_nos_override",
            "vinv_safe_inv_nos", "vinv_pipeline_raw",
            "vinv_last_push_results", "vinv_last_push_dry",
            "vinv_last_push_ok",     "vinv_last_push_err",
            "otc_tally_nos_override", "otc_pipeline_raw",
            "otc_safe_inv_nos", "otc_last_push_results",
        ]:
            st.session_state.pop(_k, None)
        st.rerun()

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PRIORITY_BASE = os.environ.get("PRIORITY_BASE", "https://us.priority-connect.online/odata/Priority/tabc5eaa.ini/aa123")
USERNAME      = os.environ.get("PRIORITY_USERNAME", "CF52658813FD4B24B43DA86CD5FDB5AD")
PASSWORD      = os.environ.get("PRIORITY_PASSWORD", "PAT")
SUBFORM_NAV   = "PORDERITEMS_SUBFORM"

TALLY_URL     = os.environ.get("TALLY_URL", "http://localhost:9000")
TALLY_COMPANY     = os.environ.get("TALLY_COMPANY", "Rishi's Test Zone")   # display name — must match Tally exactly
TALLY_COMPANY_XML = TALLY_COMPANY.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")  # XML-safe

COMPANY_STATE = "Maharashtra"  # Your company's state — used to detect inter-state (IGST) transactions

LEDGER_PURCHASE = "Purchase Account"
LEDGER_SALES    = "Sales Account"

# ─── SALES INVOICE (AINVOICES) CONFIG ─────────────────────────────────────────
# Priority entity: AINVOICES  |  Sub-form: AINVOICEITEMS_SUBFORM
# Only "Final" invoices are pushed to Tally as Sales Invoice vouchers (ISINVOICE=Yes).
SINV_FORM         = "AINVOICES"
SINV_SUBFORM      = "AINVOICEITEMS_SUBFORM"
SINV_PUSH_STATUS  = "Final"

# Priority API field → display label  (header)
SINV_HEADER_MAP = {
    "CUSTNAME":      "Customer No.",
    "CDES":          "Cust. Name",
    "IVDATE":        "Date",           # Invoice date field in AINVOICES
    "CURDATE":       "Date",           # fallback — some Priority versions use CURDATE
    "IVNUM":         "Invoice No.",
    "QPRICE":        "Total Before Discount",
    "PERCENT":       "Overall Discount (%)",
    "DISPRICE":      "Price After Discount",
    "VAT":           "GST",
    "TOTPRICE":      "Grand Total",
    "CODE":          "Currency",
    "STATDES":       "Status",
    "WARHSNAME":     "Warehouse",
    "TAXCODE":       "VAT Code",
    "PARTYVAT":      "Customer GSTIN",
    "BRANCHNAME":    "Branch",             # header-level branch code → Tally COSTCENTRENAME
    "ORDNAME":       "Order Number",       # SO reference (single SO on header)
}

# Priority API field → display label  (line items)
SINV_LINE_MAP = {
    "PARTNAME":  "Part Number",
    "PDES":      "Part Description",
    "TQUANT":    "Quantity",
    "TUNITNAME": "Unit",
    "PRICE":     "Unit Price",
    "PERCENT":   "Discount %",
    "QPRICE":    "Total Price",
    "VAT":          "Line GST",
    "ICODE":        "Item Currency",
    "WARHSNAME":    "Warehouse",
    "MAHI_TAXRATE": "GST Slab Rate",   # numeric GST % per line (e.g. 18)
    "RBS_TAXCODE":  "VAT Group",       # VAT Group code per line (e.g. "018")
    "ORDNAME":      "Order Number",    # SO reference per line (multiple SOs)
}

# ─── OTC SALES INVOICE (EINVOICES) CONFIG ─────────────────────────────────────
# Priority entity: EINVOICES  |  Sub-form: EINVOICEITEMS_SUBFORM
# Only "Final" OTC invoices are pushed to Tally as Sales vouchers (ISINVOICE=Yes).
OTC_FORM             = "EINVOICES"
OTC_SUBFORM          = "EINVOICEITEMS_SUBFORM"
OTC_STATUS_GATE      = "Final"
OTC_TALLY_VCH_TYPE   = "Sales"

OTC_HEADER_MAP = {
    "CUSTNAME":  "Customer No.",
    "CDES":      "Customer Name",
    "IVDATE":    "Date",
    "CURDATE":   "Date",
    "IVNUM":     "Invoice No.",
    "QPRICE":    "Taxable Total",
    "VAT":       "GST Amount",
    "TOTPRICE":  "Grand Total",
    "STATDES":   "Status",
    "WARHSNAME": "Warehouse",
    "PARTYVAT":  "Customer GSTIN",
    "STATENAME": "Customer State",
    "TAXCODE":   "VAT Code",
    "BRANCHNAME": "Branch",             # header-level branch code (e.g. R01-BA) → Tally COSTCENTRENAME
}

OTC_LINE_MAP = {
    "PARTNAME":     "Part Number",
    "PDES":         "Part Description",
    "TQUANT":       "Quantity",
    "TUNITNAME":    "Unit",
    "PRICE":        "Unit Price",
    "QPRICE":       "Total Price",
    "VAT":          "Line GST",
    "WARHSNAME":    "Warehouse",
    "MAHI_TAXRATE": "GST Slab Rate",
}

# ─── SALES ORDER CONFIG ───────────────────────────────────────────────────────
SO_SUBFORM_NAV   = "ORDERITEMS_SUBFORM"
SO_PUSH_STATUSES = {"Confirmed", "Final"}
SO_ALL_STATUSES  = {
    "Confirmed", "Pending Auth", "Declined", "Cancelled",
    "Canceled", "Draft", "Completed", "Partial Assm", "Final",
}

SO_HEADER_FIELD_MAP = {
    "CUSTNAME":     "Customer No.",
    "CDES":         "Cust. Name",
    "CURDATE":      "DATE",
    "ORDNAME":      "Order No.",
    "QPRICE":       "Total Before Discount",
    "PERCENT":      "Overall Discount (%)",
    "DISPRICE":     "Price After Discount",
    "TOTPRICE":     "Final Price",
    "VAT":          "GST",              # GST amount — added so party ledger = Final Price + GST
    "CODE":         "Currency",
    "ORDSTATUSDES": "Status",
    "STATDES":      "Status",
    "STAT":         "_STAT_CODE",
    "WARHSNAME":    "Sending Warehouse",  # header-level warehouse → Tally GODOWNNAME
    "BRANCHNAME":   "Branch",             # header-level branch code (e.g. R01-BA) → Tally COSTCENTRENAME
}

SO_SUBFORM_FIELD_MAP = {
    "PARTNAME":      "Part Number",
    "PDES":          "Part Description",
    "TQUANT":        "Quantity",
    "TUNITNAME":     "Unit",
    "PRICE":         "Unit Price",
    "PURCHASEPRICE": "Cost",
    "ICODE":         "Item Currency",
    "DUEDATE":       "Due Date",
    "QPRICE":        "Total Price",
    "RBS_TAXCODE":   "VAT Group",      # GST slab code per line (e.g. "005"=5%, "018"=18%)
    "WARHSNAME":     "Warehouse",
}

ELIGIBLE_STATUSES   = {"Authorised", "Completed", "Final"}
STATUS_TO_VCHTYPE   = {"Authorised": "Purchase Order", "Completed": "Purchase Order", "Final": "Purchase Order"}
STATUS_MAP_FALLBACK = {"A": "Authorised", "C": "Final", "X": "Closed"}

HEADER_FIELD_MAP = {
    "SUPNAME":      "Vendor Number",
    "CDES":         "Vendor Name",
    "CURDATE":      "Date",
    "ORDNAME":      "Order",
    "MAINDISPRICE": "Total Cost (INR)",
    "CODE":         "Currency",
    "VAT":          "VAT",
    "TAXCODE":      "VAT Code",
    "WARHSNAME":    "Warehouse",
    "STATDES":      "Status",
    "STAT":         "_STAT_CODE",
}
SUBFORM_FIELD_MAP = {
    "PARTNAME": "Part Number",
    "PDES":     "Part Description",
    "TQUANT":   "Quantity",
    "REQDATE":  "Due Date",
    "PRICE":    "Unit Price",
    "ICODE":    "Item Currency",
    "PERCENT":  "Discount %",
    "QPRICE":   "Total Price",
    "CSTM_GST": "GST",
    "PRDNO":    "Purch Demand Doc No.",
    "STATDES":  "Line Status",
}

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _auth_headers():
    token = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}

def _paginate(url, headers):
    records = []
    while url:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        d = r.json()
        records.extend(d.get("value", []))
        url = d.get("@odata.nextLink")
    return records

def fmt_inr(val):
    try: val = float(val)
    except: return "₹0"
    if pd.isna(val) or val == 0: return "₹0"
    if val >= 1_00_00_000: return f"₹{val/1_00_00_000:.2f} Cr"
    elif val >= 1_00_000:  return f"₹{val/1_00_000:.2f} L"
    return f"₹{val:,.0f}"

def fmt_cur(df, *cols):
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"₹{float(x):,.2f}" if pd.notna(x) and x != "" else "")
    return df

def _parse_dates(df, *cols):
    for col in cols:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
            df[col] = parsed.dt.tz_localize(None).dt.strftime("%d %b %Y")
    return df

def _to_num(df, *cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def _tally_date(s: str) -> str:
    s = str(s).strip()
    # Handle Priority OData /Date(1234567890000)/ format
    import re as _re
    m = _re.search(r"/Date\((-?\d+)\)/", s)
    if m:
        try:
            return datetime.utcfromtimestamp(int(m.group(1)) / 1000).strftime("%Y%m%d")
        except: pass
    for fmt in ("%d %b %Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try: return datetime.strptime(s[:10], fmt[:len(s[:10])]).strftime("%Y%m%d")
        except: pass
    return datetime.today().strftime("%Y%m%d")

def resolve_item_name(code, desc) -> str:
    """For Sales Orders only: prefer description (PDES) over code (PARTNAME).
    Used by build_so_voucher_xml. Sales Invoices (build_sinv_xml) use resolve_po_item_name
    to always prefer PARTNAME (stock code) so Tally can match existing stock items."""
    d = str(desc).strip() if desc and str(desc).strip() not in ("", "None", "nan") else ""
    c = str(code).strip() if code and str(code).strip() not in ("", "None", "nan") else ""
    return d if d else c

def resolve_po_item_name(code, desc) -> str:
    """For PO: ALWAYS prefer PARTNAME (code) over PDES (vendor description).
    e.g. PARTNAME='RM-CurryLeaf', PDES='Curry Leaf' -> returns 'RM-CurryLeaf'.
    This prevents Tally from creating phantom 'Vendor Item - Curry Leaf' stock items."""
    c = str(code).strip() if code and str(code).strip() not in ("", "None", "nan") else ""
    d = str(desc).strip() if desc and str(desc).strip() not in ("", "None", "nan") else ""
    return c if c else d

# Priority unit code → Tally unit name.
# Priority API sends short codes (kg, lt, ea …). Tally needs exact names matching the
# Units of Measure set up in the company. Extend this dict for any new codes that appear.
_PRIORITY_UNIT_MAP = {
    # Weight
    "kg":  "Kg",  "kgs": "Kg",
    "gm":  "Gms", "gms": "Gms", "g": "Gms",
    "mg":  "Mgs",
    "ton": "Ton", "mt":  "Ton",
    # Volume
    "lt":  "Ltr", "ltr": "Ltr", "l": "Ltr", "lts": "Ltr",
    "ml":  "Ml",
    # Count
    "ea":  "Nos", "nos": "Nos", "no": "Nos",
    "pcs": "Pcs", "pc":  "Pcs",
    # Packaging
    "box": "Box", "bx": "Box",
    "pkt": "Pkt",
    "bag": "Bag",
    "doz": "Doz",
    # Length / area
    "mtr": "Mtr", "m": "Mtr",
    "ft":  "Ft",
    "sqft":"Sqft",
}

def _map_priority_unit(unit_code: str):
    """Map a Priority unit code to Tally unit name. Returns None if unrecognised."""
    if not unit_code:
        return None
    return _PRIORITY_UNIT_MAP.get(unit_code.strip().lower())

# Priority warehouse code / name → Tally Godown name.
# Keys match both the short code (W01) AND the full WARHSNAME string Priority returns.
# Extend this dict whenever new warehouses are added in Priority.
_PRIORITY_GODOWN_MAP = {
    # Short codes
    "w01":       "Mumbai North Region Warehouse",
    "w02":       "Mumbai South Region Warehouse",
    "w1an":      "Andheri Outlet Warehouse",
    "w1me":      "Mulund East Outlet Warehouse",
    "w1sp":      "Shivaji Park Outlet Warehouse",
    "w2by":      "Byculla Outlet Warehouse",
    "w2cg":      "Churchgate Outlet Warehouse",
    "w2mh":      "Malabar Hill Warehouse",
    # Full names that Priority may return directly in WARHSNAME
    "mumbai north region warehouse":   "Mumbai North Region Warehouse",
    "mumbai south region warehouse":   "Mumbai South Region Warehouse",
    "andheri outlet warehouse":        "Andheri Outlet Warehouse",
    "anderi outlet warehouse":         "Andheri Outlet Warehouse",   # typo variant
    "mulund east outlet warehouse":    "Mulund East Outlet Warehouse",
    "shivaji park outlet warehouse":   "Shivaji Park Outlet Warehouse",
    "byculla outlet warehouse":        "Byculla Outlet Warehouse",
    "churchgate outlet warehouse":     "Churchgate Outlet Warehouse",
    "malabar hill warehouse":          "Malabar Hill Warehouse",
    # Tally default
    "main location":                   "Main Location",
}

def _map_priority_godown(wh_code: str) -> str:
    """Map a Priority warehouse code or name to the exact Tally Godown name.
    Falls back to original value (or Main Location) if not found."""
    if not wh_code:
        return "Main Location"
    key = wh_code.strip().lower()
    return _PRIORITY_GODOWN_MAP.get(key, wh_code.strip() or "Main Location")

def _resolve_unit(item_name: str) -> str:
    """Last-resort unit resolver by item name keywords — only when Priority sends no unit."""
    n = item_name.lower()
    if any(x in n for x in ["rice", "dal", "onion", "wheat", "sugar", "flour", "grain",
                             "leaf", "chil", "salt", "spice", "herb", "veg", "masala"]): return "Kg"
    if any(x in n for x in ["oil", "milk", "water", "juice", "liquid", "litre"]): return "Ltr"
    if any(x in n for x in ["pcs", "piece"]): return "Pcs"
    return "Nos"

def _get_unit(unit_code: str, item_name: str) -> str:
    """Primary entry point: Priority unit code first, name-based guess as fallback."""
    mapped = _map_priority_unit(unit_code)
    return mapped if mapped else _resolve_unit(item_name)

def _detect_intrastate(record: dict) -> bool:
    """
    Determine if a transaction is intra-state (CGST+SGST) or inter-state (IGST).

    Priority of checks:
    1. TAXCODE field — if Priority explicitly sends a code containing "IGST" → inter-state.
    2. STATENAME field — compare party state to COMPANY_STATE constant.
       Priority sends the party's state name in STATENAME on most forms.
    3. Default → intra-state (safest fallback for domestic transactions).
    """
    # Check 1: explicit TAXCODE / VAT Code
    tax_code = str(record.get("VAT Code") or record.get("TAXCODE") or "").strip().upper()
    if "GST_OT" in tax_code or "IGST" in tax_code:
        return False  # inter-state
    if "GST_IN" in tax_code:
        return True   # intra-state — explicit Priority flag

    # Check 2: compare party state to company state
    party_state = str(record.get("STATENAME") or record.get("State") or "").strip().upper()
    company_state = COMPANY_STATE.strip().upper()
    if party_state and party_state != company_state:
        return False  # inter-state — different states

    # Check 3: default intra-state
    return True


# ─── ITEM-WISE GST GROUPING (MAHI_TAXRATE) ────────────────────────────────────
# These helpers implement the new Priority item-level GST logic.
# Priority now stores the GST slab per line in MAHI_TAXRATE (e.g. 5, 12, 18, 28).
# We group items by slab and emit a separate Tally ledger entry per slab.
#
# Ledger naming convention (direction-aware — see _gst_ledger_name()):
#   Purchase-side (direction="input")  : "Input CGST @ 2.5% Recoverable", "Input SGST @ 2.5% Recoverable",
#                                         "Input IGST @ 18% Recoverable", etc.
#   Sales-side    (direction="output") : "Output CGST @ 2.5% Payable",   "Output SGST @ 2.5% Payable",
#                                         "Output IGST @ 18% Payable",   etc.
#
# These ledger names MUST exist in Tally (already created from the Priority COA).
# Modules pass direction="input" for GRV/Multi-GRV/Vendor Invoice/PO,
# and direction="output" for Sales Order/Sales Invoice/OTC/Multi Shipment Invoice/Shipment.

# Priority VAT Group codes that mean EXEMPT (0% GST).
# "001" is the standard exempt code; add others here if needed.
_EXEMPT_VAT_GROUPS = {"001", "000", "0", "999"}  # 999 = Priority exempt/nil (e.g. RM-Water)

def _decode_mahi_taxrate(raw) -> float:
    """
    Convert a Priority MAHI_TAXRATE value to a numeric GST %.

    Priority stores this as a VAT Group code string, e.g.:
      "001" -> 0%  (exempt -- leading zeros do not mean 1%)
      "005" -> 5%
      "018" -> 18%
      "028" -> 28%
      18.0  -> 18% (already numeric, pass through)

    Exempt codes in _EXEMPT_VAT_GROUPS always return 0.0.
    For other codes: strip leading zeros and convert to float.
    """
    if raw is None:
        return 0.0
    s = str(raw).strip()
    if s in _EXEMPT_VAT_GROUPS:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0

def _gst_ledger_name(tax_type: str, rate_str: str, direction: str) -> str:
    """
    Build the exact Tally GST ledger name for a given tax type/rate/direction.

    direction: "input"  -> purchase-side ITC   -> "Input {TYPE} @ {rate}% Recoverable"
               "output" -> sales-side liability -> "Output {TYPE} @ {rate}% Payable"

    These ledger names must already exist in Tally (created from the Priority COA).
    Example: _gst_ledger_name("CGST", "2.5", "input")  -> "Input CGST @ 2.5% Recoverable"
             _gst_ledger_name("IGST", "18",  "output") -> "Output IGST @ 18% Payable"
    """
    direction = (direction or "input").strip().lower()
    tax_type = tax_type.strip().upper()
    if direction == "output":
        return f"Output {tax_type} @ {rate_str}% Payable"
    return f"Input {tax_type} @ {rate_str}% Recoverable"


def _build_gst_groups(raw_lines: list, is_intrastate: bool,
                      amt_field: str = "QPRICE",
                      gst_field: str = "CSTM_GST",
                      direction: str = "input") -> dict:
    """
    Build item-wise GST groups from line items using MAHI_TAXRATE.

    For each line:
      - Read MAHI_TAXRATE directly (e.g. 5, 12, 18, 28).
      - Compute GST rupee amount from (taxable_amount × MAHI_TAXRATE / 100).
      - Group by slab into ledger-name-keyed dict.

    Fallback chain if MAHI_TAXRATE is absent on a line:
      1. If a rupee-amount GST field (gst_field) is available, back-calculate
         the rate from (gst_amt / taxable_amt * 100) and round to nearest slab.
      2. If nothing is available, skip the line (contributes 0 GST).

    Returns a dict keyed by full Tally ledger name → cumulative GST amount (float).
    direction ("input" or "output") controls whether names resolve to the
    "Input ... Recoverable" or "Output ... Payable" ledgers (see _gst_ledger_name()).
    Example (GST_IN, input):  {"Input CGST @ 2.5% Recoverable": 2.5, "Input SGST @ 2.5% Recoverable": 2.5}
    Example (GST_OT, output): {"Output IGST @ 18% Payable": 18.0}
    """
    groups: dict[str, float] = {}

    for line in raw_lines:
        # ── Taxable amount for this line ──────────────────────────────────────
        try:
            amt = float(line.get(amt_field) or line.get("QPRICE") or line.get("Total Price") or 0)
        except Exception:
            amt = 0.0
        if amt <= 0:
            continue

        # ── Read MAHI_TAXRATE directly ────────────────────────────────────────
        raw_taxrate = line.get("MAHI_TAXRATE")
        if raw_taxrate is not None:
            try:
                taxrate = _decode_mahi_taxrate(raw_taxrate)
            except Exception:
                taxrate = 0.0
        else:
            # Fallback: back-calculate from rupee GST field
            try:
                gst_amt_raw = float(line.get(gst_field) or line.get("CSTM_GST")
                                    or line.get("VAT") or line.get("Line GST") or 0)
            except Exception:
                gst_amt_raw = 0.0
            if gst_amt_raw > 0 and amt > 0:
                raw_rate = gst_amt_raw / amt * 100
                # Round to nearest standard GST slab
                taxrate = min([5, 12, 18, 28], key=lambda s: abs(s - raw_rate))
            else:
                taxrate = 0.0

        if taxrate <= 0:
            continue

        # ── Compute line GST amount from MAHI_TAXRATE ─────────────────────────
        line_gst = round(amt * taxrate / 100, 2)

        # ── Map to Tally ledger name(s) ───────────────────────────────────────
        if is_intrastate:
            # Each half: CGST = taxrate/2, SGST = taxrate/2
            half = taxrate / 2
            # Format: "2.5" not "2.50" — matches typical Tally ledger naming
            half_str = f"{half:g}"
            cgst_key = _gst_ledger_name("CGST", half_str, direction)
            sgst_key = _gst_ledger_name("SGST", half_str, direction)
            half_amt = round(line_gst / 2, 2)
            groups[cgst_key] = round(groups.get(cgst_key, 0.0) + half_amt, 2)
            groups[sgst_key] = round(groups.get(sgst_key, 0.0) + half_amt, 2)
        else:
            taxrate_str = f"{taxrate:g}"
            igst_key = _gst_ledger_name("IGST", taxrate_str, direction)
            groups[igst_key] = round(groups.get(igst_key, 0.0) + line_gst, 2)

    return groups


def _gst_group_ledger_entries(gst_groups: dict, is_intrastate: bool,
                               isdeemedpositive: str = "Yes",
                               sign: str = "-") -> str:
    """
    Generate Tally LEDGERENTRIES.LIST XML blocks for each GST slab group.

    Parameters
    ----------
    gst_groups        : output of _build_gst_groups()
    is_intrastate     : True → CGST/SGST ledgers, False → IGST ledgers
    isdeemedpositive  : "Yes" for purchase-side ITC debit; "No" for sales output tax
    sign              : "-" for debit (purchase/GRV); "" for positive (sales)

    The ledger names in gst_groups must already exist in Tally.
    """
    entries = ""
    # Sort for consistent ordering: CGST before SGST, then by rate
    for ledger_name in sorted(gst_groups.keys()):
        amt = gst_groups[ledger_name]
        if amt <= 0:
            continue
        entries += f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{ledger_name}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>{isdeemedpositive}</ISDEEMEDPOSITIVE>
                            <AMOUNT>{sign}{amt:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
    return entries


def _get_item_gst_rate_pcts(line: dict, is_intrastate: bool,
                             fallback_total_gst_pct: float = 0.0) -> tuple[float, float, float]:
    """
    Resolve CGST%, SGST%, IGST% for a single line item's RATEDETAILS.LIST block.
    Reads MAHI_TAXRATE directly; falls back to the caller-supplied total %.
    Returns (cgst_pct, sgst_pct, igst_pct).
    """
    raw_taxrate = line.get("MAHI_TAXRATE")
    if raw_taxrate is not None:
        try:
            taxrate = _decode_mahi_taxrate(raw_taxrate)
        except Exception:
            taxrate = fallback_total_gst_pct
    else:
        taxrate = fallback_total_gst_pct

    if is_intrastate:
        half = round(taxrate / 2, 2)
        return half, half, taxrate          # cgst, sgst, igst (igst unused but returned)
    else:
        return 0.0, 0.0, taxrate            # cgst/sgst unused; igst = full rate


# ─── TALLY XML BUILDERS (Purchase Order & Sales Order) ───────────────────────
def _inv_lines(raw_lines: list, tally_date: str, warehouse: str, ord_name: str, branch: str = "") -> str:
    """
    Build ALLINVENTORYENTRIES.LIST blocks for a Purchase Order voucher.
    - Inventory amounts are negative (debit side).
    - RATE includes unit: 140.00/Kg
    - ACTUALQTY / BILLEDQTY include unit: 5.00 Kg
    - Includes RATEDETAILS.LIST (CGST/SGST/IGST per line) so Tally knows item-level GST rate.
    - Does NOT emit GST ledger entries here — those are accumulated and emitted in build_voucher_xml.
    """
    out = ""
    wh = warehouse or "Main Location"
    for line in raw_lines:
        name = resolve_po_item_name(
            line.get("PARTNAME") or line.get("Part Number", ""),
            line.get("PDES")     or line.get("Part Description", ""),
        )
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT")  or line.get("Quantity",   0))
            rate = float(line.get("PRICE")   or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE")  or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        # Priority supplies GST as a rupee amount per line (CSTM_GST field)
        try:
            line_gst_amt = float(line.get("CSTM_GST") or line.get("GST") or 0)
        except Exception:
            line_gst_amt = 0.0

        # ── NEW: Read GST% directly from MAHI_TAXRATE ─────────────────────────
        # Fallback: back-calculate from CSTM_GST rupee amount if MAHI_TAXRATE absent.
        raw_taxrate = line.get("MAHI_TAXRATE")
        if raw_taxrate is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(raw_taxrate)
            except Exception:
                total_gst_pct = 0.0
        elif amt > 0 and line_gst_amt > 0:
            total_gst_pct = round(line_gst_amt / amt * 100, 2)
        else:
            total_gst_pct = 0.0

        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        raw_unit = str(line.get("TUNITNAME") or line.get("Unit") or "").strip()
        unit = _get_unit(raw_unit, name)

        due_raw  = line.get("REQDATE") or line.get("Due Date", "")
        prd_no   = line.get("PRDNO")   or line.get("Purch Demand Doc No.", "") or ord_name

        try:
            due_date = pd.to_datetime(str(due_raw)).strftime("%d-%b-%y") if due_raw else datetime.today().strftime("%d-%b-%y")
        except Exception:
            due_date = datetime.today().strftime("%d-%b-%y")

        # RATEDETAILS.LIST tells Tally the GST rate per item — critical for GST reports
        rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>""" if total_gst_pct > 0 else ""

        _cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch}</NAME>
                            <AMOUNT>-{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        out += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>-{amt:.2f}</AMOUNT>
                <ACTUALQTY>{qty:.2f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.2f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{wh}</DESTINATIONGODOWNNAME>
                    <ORDERNO>{prd_no}</ORDERNO>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.2f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.2f} {unit}</BILLEDQTY>
                    <ORDERDUEDATE>{due_date}</ORDERDUEDATE>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_PURCHASE}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    {_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""
    return out


def build_voucher_xml(order: dict) -> str:
    """
    Build a Tally-compatible Purchase Order XML envelope with full GST support.

    GST logic:
    - Priority supplies CSTM_GST (rupee amount) per line item in PORDERITEMS_SUBFORM.
    - We sum CGST and SGST (intra-state, same state) or IGST (inter-state) from line amounts.
    - is_intrastate = vendor STATENAME matches company CMPGSTSTATE.
      For Priority API records this is inferred from the VAT/TAXCODE field or assumed
      intra-state (most common for domestic raw material purchases).
    - The LEDGERENTRIES for CGST/SGST/IGST are emitted at the voucher footer.
    - Party ledger amount = taxable total + total GST (i.e. Priority's FINAL PRICE / MAINDISPRICE + VAT).
    - Each inventory line also carries RATEDETAILS.LIST so Tally knows the per-item GST rate.

    Ledger names must exist in Tally (direction="input" — purchase side):
      Intra-state : "Input CGST @ {rate}% Recoverable" + "Input SGST @ {rate}% Recoverable"
      Inter-state : "Input IGST @ {rate}% Recoverable"
    """
    status   = order.get("Status") or order.get("STATDES") or ""
    vch_type = STATUS_TO_VCHTYPE.get(status)
    if not vch_type:
        return ""

    ord_name  = order.get("Order")            or order.get("ORDNAME", "")
    raw_date  = order.get("Date")             or order.get("CURDATE", "")
    vendor    = order.get("Vendor Name")      or order.get("CDES", "")
    taxable   = float(order.get("Total Cost (INR)") or order.get("MAINDISPRICE") or 0)
    warehouse = order.get("Warehouse")        or order.get("WARHSNAME", "Main Location")
    branch    = str(
        order.get("BRANCHNAME") or order.get("Branch") or
        order.get("BRANCH")     or order.get("BRANCHDES") or ""
    ).strip()
    raw_lines = order.get(SUBFORM_NAV)        or []

    # ── GST computation using item-wise MAHI_TAXRATE ──────────────────────────
    is_intrastate = _detect_intrastate(order)  # TAXCODE + STATENAME vs COMPANY_STATE

    # Build slab-wise GST groups from MAHI_TAXRATE (falls back to CSTM_GST back-calculation)
    gst_groups = _build_gst_groups(raw_lines, is_intrastate, gst_field="CSTM_GST", direction="input")

    total_gst = round(sum(gst_groups.values()), 2)

    # If Priority header-level VAT differs (rounding), scale groups proportionally
    header_vat = 0.0
    try:
        header_vat = float(order.get("VAT") or 0)
    except Exception:
        pass
    if header_vat > 0 and total_gst > 0 and abs(header_vat - total_gst) > 0.05:
        # Proportionally scale all group amounts to match header VAT
        scale = header_vat / total_gst
        gst_groups = {k: round(v * scale, 2) for k, v in gst_groups.items()}
        total_gst = round(sum(gst_groups.values()), 2)
    elif header_vat > 0 and total_gst == 0:
        # No line-level GST data at all — fall back to flat split from header VAT
        total_gst = round(header_vat, 2)
        if is_intrastate:
            gst_groups = {
                _gst_ledger_name("CGST", "9", "input"): round(total_gst / 2, 2),
                _gst_ledger_name("SGST", "9", "input"): round(total_gst - round(total_gst / 2, 2), 2),
            }
        else:
            gst_groups = {_gst_ledger_name("IGST", "18", "input"): total_gst}

    grand_total = round(taxable + total_gst, 2)

    t_date    = _tally_date(str(raw_date))
    narration = "Authorised in Priority ERP"
    inv_lines = _inv_lines(raw_lines, t_date, warehouse, ord_name, branch)

    # ── Slab-wise GST ledger entries (footer) — one entry per GST slab ─────────
    gst_entries = _gst_group_ledger_entries(
        gst_groups, is_intrastate, isdeemedpositive="Yes", sign="-"
    )

    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase Order" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Purchase Order</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{ord_name}</VOUCHERNUMBER>
                        <REFERENCE>{ord_name}</REFERENCE>
                        <PARTYLEDGERNAME>{vendor}</PARTYLEDGERNAME>
                        <PARTYNAME>{vendor}</PARTYNAME>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>{narration}</NARRATION>
                        <ISINVOICE>No</ISINVOICE>
                        <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        {inv_lines}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{vendor}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{grand_total:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{gst_entries}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_sales_orders():
    hdrs = _auth_headers()
    # $select is required — Priority OData silently drops BRANCHNAME (and other
    # non-standard fields) from the response unless they are explicitly requested.
    so_header_select = (
        "CUSTNAME,CDES,CURDATE,ORDNAME,QPRICE,PERCENT,DISPRICE,"
        "TOTPRICE,VAT,CODE,ORDSTATUSDES,STATDES,STAT,WARHSNAME,BRANCHNAME"
    )
    url  = (f"{PRIORITY_BASE}/ORDERS"
            f"?$select={so_header_select}"
            f"&$expand={SO_SUBFORM_NAV}"
            f"&$top=500")
    try:
        records   = _paginate(url, hdrs)
        has_lines = any(
            isinstance(r.get(SO_SUBFORM_NAV), list) and len(r.get(SO_SUBFORM_NAV, [])) > 0
            for r in records
        )
        return records, has_lines
    except Exception:
        try:
            # Fallback without $select (BRANCHNAME may be absent — better than nothing)
            fallback = _paginate(
                f"{PRIORITY_BASE}/ORDERS?$expand={SO_SUBFORM_NAV}&$top=500", hdrs
            )
            return fallback, False
        except Exception:
            return [], False

def build_so_header_df(raw):
    df = pd.DataFrame(raw)
    if SO_SUBFORM_NAV in df.columns:
        df = df.drop(columns=[SO_SUBFORM_NAV])
    rename = {k: v for k, v in SO_HEADER_FIELD_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)
    if "Status" not in df.columns and "_STAT_CODE" in df.columns:
        df["Status"] = df["_STAT_CODE"].map(STATUS_MAP_FALLBACK).fillna(df["_STAT_CODE"])
    df = df.drop(columns=["_STAT_CODE"], errors="ignore")
    df = _parse_dates(df, "DATE")
    df = _to_num(df, "Total Before Discount", "Overall Discount (%)", "Price After Discount", "Final Price", "GST")
    return df

def build_so_lines_df(raw):
    rows = []
    for order in raw:
        lines = order.get(SO_SUBFORM_NAV, [])
        if not lines:
            continue
        base = {
            "Order No.":    order.get("ORDNAME"),
            "Cust. Name":   order.get("CDES"),
            "DATE":         order.get("CURDATE"),
            "Header Status": (
                order.get("ORDSTATUSDES") or order.get("STATDES")
                or STATUS_MAP_FALLBACK.get(order.get("STAT", ""), order.get("STAT", ""))
            ),
        }
        for line in lines:
            row = {**base}
            for api, friendly in SO_SUBFORM_FIELD_MAP.items():
                row[friendly] = line.get(api)
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "DATE", "Due Date")
    df = _to_num(df, "Quantity", "Unit Price", "Cost", "Total Price")
    return df

def build_so_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy()
        df["Line Count"]  = 0
        df["Parts"]       = ""
        df["Lines Total"] = 0.0
        return df
    agg = (
        lines_df.groupby("Order No.")
        .agg(
            LC=("Part Description", "count"),
            LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
            LT=("Total Price", "sum"),
        )
        .reset_index()
        .rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"})
    )
    merged = header_df.merge(agg, on="Order No.", how="left")
    merged["Line Count"]  = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"]       = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged

def build_so_voucher_xml(order: dict) -> str:
    """
    Build a Tally Sales Order XML voucher from a Priority ORDERS record.

    Priority → Tally field mapping:
      CDES         → PARTYLEDGERNAME / PARTYNAME  (Sundry Debtors)
      CURDATE      → DATE (YYYYMMDD)
      ORDNAME      → VOUCHERNUMBER / REFERENCE
      TOTPRICE     → grand total (taxable + GST)
      VAT (header) → total GST amount (split into CGST+SGST or IGST)
      ORDERITEMS_SUBFORM:
        PARTNAME   → STOCKITEMNAME
        TQUANT     → BILLEDQTY / ACTUALQTY
        TUNITNAME  → unit suffix
        PRICE      → RATE
        QPRICE     → line AMOUNT
        DUEDATE    → ORDERDUEDATE  DD-Mon-YY
        VATGROUP   → per-line GST slab (e.g. "005"=5%, "018"=18%, "028"=28%)

    GST ledger naming (direction="output" — sales side; must exist in Tally):
      Intra-state: "Output CGST @ {half_rate}% Payable" + "Output SGST @ {half_rate}% Payable"
      Inter-state: "Output IGST @ {full_rate}% Payable"
    If VATGROUP is absent on all lines, falls back to proportional distribution of header VAT.
    """
    ord_name  = order.get("Order No.")  or order.get("ORDNAME", "")
    raw_date  = order.get("DATE")       or order.get("CURDATE", "")
    customer  = order.get("Cust. Name") or order.get("CDES", "")
    # WARHSNAME is a main-form field on ORDERS (not on subform lines).
    # Use the raw code directly — Tally godowns are named by the short code (e.g. W1AN),
    # NOT the full warehouse name. Do NOT pass through _map_priority_godown here.
    header_wh = str(order.get("WARHSNAME") or "").strip() or "Main Location"
    # BRANCHNAME / BRANCH / BRANCHDES — Priority field name varies by form/version.
    # Try all known variants; also accept the friendly key "Branch" if the dict was
    # already renamed by build_so_header_df before being passed here.
    branch    = str(
        order.get("BRANCHNAME") or order.get("Branch") or
        order.get("BRANCH")     or order.get("BRANCHDES") or
        order.get("BRANCHCODE") or ""
    ).strip()

    gst_total = float(order.get("GST") or order.get("VAT") or 0)
    disprice  = float(order.get("Price After Discount") or order.get("DISPRICE") or 0)
    totprice  = float(order.get("Final Price") or order.get("TOTPRICE") or 0)
    grand_total = round(totprice if totprice >= disprice and totprice > 0 else disprice + gst_total, 2)

    t_date    = _tally_date(str(raw_date))
    raw_lines = order.get(SO_SUBFORM_NAV) or []

    # ── Intra vs inter-state (TAXCODE GST_OT/GST_IN or STATENAME vs COMPANY_STATE) ──
    is_intrastate = _detect_intrastate(order)

    # ── Resolve per-line VAT Group → GST % ─────────────────────────────────
    # VATGROUP field (e.g. "005", "012", "018", "028") is the new Priority column.
    # _decode_mahi_taxrate handles the leading-zero logic already.
    def _line_gst_pct(line) -> float:
        raw = line.get("RBS_TAXCODE") or line.get("VAT Group")
        return _decode_mahi_taxrate(raw)

    any_vatgroup = any(_line_gst_pct(l) > 0 for l in raw_lines)

    # ── Inventory line blocks ───────────────────────────────────────────────
    inv_out = ""
    for line in raw_lines:
        stock_name = resolve_po_item_name(
            line.get("PARTNAME") or line.get("Part Number", ""),
            line.get("PDES")     or line.get("Part Description", ""),
        )
        if not stock_name:
            continue

        try:
            qty     = float(line.get("TQUANT") or line.get("Quantity", 0))
            amt     = float(line.get("QPRICE") or line.get("Total Price", 0))
            _rr     = float(line.get("PRICE") or line.get("Unit Price") or 0)
            rate    = _rr if _rr > 0 else (round(amt / qty, 2) if qty > 0 else amt)
        except Exception:
            qty = rate = amt = 0.0

        raw_unit = str(line.get("TUNITNAME") or line.get("Unit", "")).strip()
        unit     = raw_unit if raw_unit else _resolve_unit(stock_name)

        due_raw = line.get("DUEDATE") or line.get("Due Date", "")
        try:
            due_date = (pd.to_datetime(str(due_raw)).strftime("%d-%b-%y")
                        if due_raw else datetime.today().strftime("%d-%b-%y"))
        except Exception:
            due_date = datetime.today().strftime("%d-%b-%y")

        # Per-line GST % for RATEDETAILS
        if any_vatgroup:
            total_gst_pct = _line_gst_pct(line)
        else:
            # Fallback: proportional share of header VAT
            total_line_amt = sum(float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines) or 1.0
            line_share = round(gst_total * (amt / total_line_amt), 2) if total_line_amt > 0 else 0.0
            total_gst_pct = round(line_share / amt * 100, 2) if amt > 0 and line_share > 0 else 0.0

        if is_intrastate:
            cgst_pct = round(total_gst_pct / 2, 2)
            sgst_pct = round(total_gst_pct / 2, 2)
            igst_pct = 0.0
        else:
            cgst_pct = sgst_pct = 0.0
            igst_pct = total_gst_pct

        rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>""" if total_gst_pct > 0 else ""

        # WARHSNAME is only on the ORDERS main form (header_wh), not on subform lines.
        # Fall back to header_wh so the correct godown (e.g. W1AN) reaches Tally.
        # Use the raw code directly — Tally godowns are named by the short code (e.g. W1AN).
        line_wh = str(line.get("WARHSNAME") or line.get("Warehouse") or "").strip() or header_wh

        _so_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch}</NAME>
                            <AMOUNT>{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        inv_out += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{stock_name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>{amt:.2f}</AMOUNT>
                <ACTUALQTY>{qty:.2f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.2f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <ORDERNO>{ord_name}</ORDERNO>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.2f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.2f} {unit}</BILLEDQTY>
                    <ORDERDUEDATE>{due_date}</ORDERDUEDATE>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_SALES}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    {_so_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # ── GST ledger entries — grouped by slab (CGST N / SGST N or IGST N) ────
    # Build slab buckets from per-line VATGROUP codes.
    gst_entries = ""
    if gst_total > 0:
        if any_vatgroup:
            # Group lines by GST slab and sum amounts per slab
            slab_taxable: dict[float, float] = {}
            for line in raw_lines:
                try:
                    amt = float(line.get("QPRICE") or line.get("Total Price") or 0)
                except Exception:
                    amt = 0.0
                slab = _line_gst_pct(line)
                if slab > 0 and amt > 0:
                    slab_taxable[slab] = slab_taxable.get(slab, 0.0) + amt

            for slab_rate, taxable_amt in sorted(slab_taxable.items()):
                slab_gst = round(taxable_amt * slab_rate / 100, 2)
                if is_intrastate:
                    half = round(slab_gst / 2, 2)
                    other_half = round(slab_gst - half, 2)
                    half_rate = round(slab_rate / 2, 4)
                    # Remove trailing zeros: 9.0 → "9", 2.5 → "2.5"
                    hr = f"{half_rate:g}"
                    gst_entries += f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_gst_ledger_name("CGST", hr, "output")}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{half:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_gst_ledger_name("SGST", hr, "output")}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{other_half:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
                else:
                    sr = f"{slab_rate:g}"
                    gst_entries += f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_gst_ledger_name("IGST", sr, "output")}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{slab_gst:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
        else:
            # Fallback: no VATGROUP — use header GST total, split 9/9 (or full IGST)
            if is_intrastate:
                cgst_amt = round(gst_total / 2, 2)
                sgst_amt = round(gst_total - cgst_amt, 2)
                gst_entries = f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_gst_ledger_name("CGST", "9", "output")}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{cgst_amt:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_gst_ledger_name("SGST", "9", "output")}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{sgst_amt:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
            else:
                gst_entries = f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_gst_ledger_name("IGST", "18", "output")}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{gst_total:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""

    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales Order" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{ord_name}</VOUCHERNUMBER>
                        <REFERENCE>{ord_name}</REFERENCE>
                        <PARTYLEDGERNAME>{customer}</PARTYLEDGERNAME>
                        <PARTYNAME>{customer}</PARTYNAME>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Confirmed in Priority ERP</NARRATION>
                        <ISINVOICE>No</ISINVOICE>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        {inv_out}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{customer}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{grand_total:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{gst_entries}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()

    return xml.strip()



# ─── SALES INVOICE — FETCH & BUILD ────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_sales_invoices():
    """Fetch Final Sales Invoices from Priority AINVOICES with expanded line items.

    $select is required — Priority OData silently drops non-standard fields
    (MAHI_TAXRATE, RBS_TAXCODE, BRANCHNAME) unless explicitly requested.
    Falls back to bare $expand, then headers-only as last resort.
    """
    hdrs = _auth_headers()
    sinv_header_select = (
        "CUSTNAME,CDES,IVDATE,CURDATE,IVNUM,QPRICE,PERCENT,DISPRICE,"
        "VAT,TOTPRICE,CODE,STATDES,WARHSNAME,TAXCODE,PARTYVAT,BRANCHNAME,ORDNAME"
    )
    sinv_line_select = (
        "PARTNAME,PDES,TQUANT,TUNITNAME,PRICE,PERCENT,QPRICE,VAT,"
        "MAHI_TAXRATE,RBS_TAXCODE,ICODE,WARHSNAME,ORDNAME"
    )
    attempts = [
        (
            f"{PRIORITY_BASE}/{SINV_FORM}"
            f"?$select={sinv_header_select}"
            f"&$expand={SINV_SUBFORM}($select={sinv_line_select})"
            f"&$top=500"
        ),
        f"{PRIORITY_BASE}/{SINV_FORM}?$expand={SINV_SUBFORM}&$top=500",
        f"{PRIORITY_BASE}/{SINV_FORM}?$top=500",
    ]
    for url in attempts:
        try:
            records = _paginate(url, hdrs)
            if records is not None:
                has_lines = any(
                    isinstance(r.get(SINV_SUBFORM), list) and len(r[SINV_SUBFORM]) > 0
                    for r in records
                )
                return records, has_lines
        except Exception:
            continue
    return [], False

def build_sinv_header_df(raw):
    df = pd.DataFrame(raw)
    if SINV_SUBFORM in df.columns:
        df = df.drop(columns=[SINV_SUBFORM])
    # If both IVDATE and CURDATE exist, prefer IVDATE (the actual invoice date in AINVOICES)
    if "IVDATE" in df.columns and "CURDATE" in df.columns:
        df["IVDATE"] = df["IVDATE"].fillna(df["CURDATE"])
        df = df.drop(columns=["CURDATE"])
    df = df.rename(columns={k: v for k, v in SINV_HEADER_MAP.items() if k in df.columns})
    # If Date column still missing, it means neither IVDATE nor CURDATE came back — leave blank
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Total Before Discount", "Overall Discount (%)", "Price After Discount", "GST", "Grand Total")
    return df

def build_sinv_lines_df(raw):
    rows = []
    for inv in raw:
        lines = inv.get(SINV_SUBFORM, [])
        if not lines:
            continue
        base = {
            "Invoice No.": inv.get("IVNUM"),
            "Cust. Name":  inv.get("CDES"),
            "Date":        inv.get("IVDATE") or inv.get("CURDATE"),
            "Status":      inv.get("STATDES", ""),
            "Warehouse":   inv.get("WARHSNAME", ""),
        }
        for line in lines:
            row = {**base, **{v: line.get(k) for k, v in SINV_LINE_MAP.items()}}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Quantity", "Unit Price", "Discount %", "Total Price", "Line GST")
    return df

def build_sinv_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy()
        df["Line Count"] = 0; df["Parts"] = ""; df["Lines Total"] = 0.0
        return df
    agg = (
        lines_df.groupby("Invoice No.")
        .agg(
            LC=("Part Description", "count"),
            LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
            LT=("Total Price", "sum"),
        )
        .reset_index()
        .rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"})
    )
    merged = header_df.merge(agg, on="Invoice No.", how="left")
    merged["Line Count"]  = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"]       = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged

def build_sinv_xml(inv: dict) -> str:
    """
    Build a Tally Sales Invoice XML (ISINVOICE=Yes) from a Priority AINVOICES record.

    Sign convention verified against real Tally Sales Invoice XML (Sales_23.xml):
      - ALLINVENTORYENTRIES  ISDEEMEDPOSITIVE=No,  AMOUNT positive  (stock goes out)
      - ACCOUNTINGALLOCATIONS (Sales Account)  ISDEEMEDPOSITIVE=No,  AMOUNT positive
      - Party LEDGERENTRIES  ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (customer owes us)
      - CGST/SGST             ISDEEMEDPOSITIVE=No,  AMOUNT positive  (output tax liability)

    Priority → Tally field mapping:
      IVNUM        → VOUCHERNUMBER / REFERENCE
      CURDATE      → DATE (YYYYMMDD)
      CDES         → PARTYLEDGERNAME / PARTYNAME   (Sundry Debtors)
      PARTYGSTIN   → PARTYGSTIN (customer GSTIN from Priority GSTIN field)
      TOTPRICE     → party LEDGERENTRIES AMOUNT (negative)
      VAT (header) → CGST + SGST (or IGST) LEDGERENTRIES (positive)
      WARHSNAME    → GODOWNNAME via _PRIORITY_GODOWN_MAP
      AINVOICEITEMS:
        PARTNAME / PDES → STOCKITEMNAME
        TQUANT          → BILLEDQTY / ACTUALQTY   e.g. "1.0000 ea"
        TUNITNAME       → unit suffix
        PRICE           → RATE                    e.g. "140.00/ea"
        QPRICE          → line AMOUNT (positive)
        WARHSNAME       → GODOWNNAME per line
    """
    inv_no    = inv.get("Invoice No.") or inv.get("IVNUM", "")
    raw_date  = inv.get("Date")        or inv.get("IVDATE", "") or inv.get("CURDATE", "")
    customer  = inv.get("Cust. Name")  or inv.get("CDES", "")
    warehouse = inv.get("Warehouse")   or inv.get("WARHSNAME", "Main Location")
    branch    = str(
        inv.get("BRANCHNAME") or inv.get("Branch") or
        inv.get("BRANCH")     or inv.get("BRANCHDES") or ""
    ).strip()
    grand_tot = float(inv.get("Grand Total") or inv.get("TOTPRICE") or 0)
    gst_total = float(inv.get("GST")         or inv.get("VAT")      or 0)
    party_gstin = str(inv.get("PARTYGSTIN") or "").strip()
    t_date    = _tally_date(str(raw_date))

    # Intra vs inter-state: check TAXCODE/VATCODE from header
    is_intrastate = _detect_intrastate(inv)    # TAXCODE + STATENAME vs COMPANY_STATE

    # Warehouse name mapping: Priority code → Tally godown name
    _wh = _map_priority_godown(warehouse)

    raw_lines = inv.get(SINV_SUBFORM) or []

    # ── Collect unique SO numbers — mirrors Multi Shipment DOCNO logic ────────
    # Single SO: ORDNAME on the invoice header.
    # Multiple SOs: ORDNAME on each AINVOICEITEMS subform line (deduplicated,
    # insertion-order preserved so they appear in the same sequence in Tally).
    _seen_so = set()
    all_so_nos = []
    for _l in raw_lines:
        _s = str(_l.get("ORDNAME") or _l.get("Order Number") or "").strip()
        if _s and _s not in _seen_so:
            _seen_so.add(_s)
            all_so_nos.append(_s)
    # Fallback: header-level ORDNAME (single SO or no subform)
    if not all_so_nos:
        _hdr_so = str(inv.get("ORDNAME") or inv.get("Order Number") or "").strip()
        if _hdr_so:
            all_so_nos = [_hdr_so]

    # One INVOICEORDERLIST.LIST block per SO — same structure as Multi Shipment.
    # BASICPURCHASEORDERNO is the correct Tally tag for "Order No(s)" field.
    if all_so_nos:
        _order_list_blocks = "".join(f"""
                        <INVOICEORDERLIST.LIST>
                            <BASICORDERDATE>{t_date}</BASICORDERDATE>
                            <BASICPURCHASEORDERNO>{_so}</BASICPURCHASEORDERNO>
                        </INVOICEORDERLIST.LIST>""" for _so in all_so_nos)
    else:
        _order_list_blocks = """
                        <INVOICEORDERLIST.LIST>      </INVOICEORDERLIST.LIST>"""

    inv_entries = ""
    for line in raw_lines:
        pn   = str(line.get("PARTNAME") or line.get("Part Number", "")).strip()
        pd_  = str(line.get("PDES")     or line.get("Part Description", "")).strip()
        name = resolve_po_item_name(pn, pd_)   # always prefer PARTNAME (stock code) over PDES
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT") or line.get("Quantity",   0))
            rate = float(line.get("PRICE")  or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE") or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        # Use raw Priority unit directly (same as SO — avoid unit mismatch in Tally)
        raw_unit = str(line.get("TUNITNAME") or line.get("Unit", "")).strip()
        unit = raw_unit if raw_unit else _resolve_unit(name)

        # Per-line warehouse: use raw Priority code directly — Tally stores godowns by
        # the short code (e.g. W1AN, W1ME) as confirmed by Sales_25.xml export.
        # Do NOT remap to full names; Tally won't find "Andheri Outlet Warehouse".
        line_wh_raw = str(line.get("WARHSNAME") or line.get("Warehouse") or warehouse or "Main Location").strip()
        line_wh = line_wh_raw if line_wh_raw else "Main Location"

        # Per-line SO reference — ORDNAME on each subform line links this item
        # back to the originating Sales Order in Tally's item allocation view.
        line_so = str(line.get("ORDNAME") or line.get("Order Number") or "").strip()

        # GST % resolution — three-tier chain (same as OTC / Multi Shipment):
        # 1. MAHI_TAXRATE — numeric % direct (e.g. 18)
        # 2. RBS_TAXCODE  — VAT Group code (e.g. "018")
        # 3. Line VAT rupee → back-calculate; proportional header fallback last.
        raw_taxrate = line.get("MAHI_TAXRATE")
        raw_rbs     = line.get("RBS_TAXCODE")
        total_gst_pct = 0.0
        if raw_taxrate is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(raw_taxrate)
            except Exception:
                total_gst_pct = 0.0
        if total_gst_pct == 0.0 and raw_rbs is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(raw_rbs)
            except Exception:
                total_gst_pct = 0.0
        if total_gst_pct == 0.0:
            try:
                line_vat = float(line.get("VAT") or line.get("Line GST") or 0)
            except Exception:
                line_vat = 0.0
            if line_vat <= 0 and amt > 0 and gst_total > 0:
                total_line_amt = sum(
                    float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines
                ) or 1.0
                line_vat = round(gst_total * (amt / total_line_amt), 2)
            total_gst_pct = round(line_vat / amt * 100, 2) if amt > 0 and line_vat > 0 else 0.0

        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        if total_gst_pct > 0:
            if is_intrastate:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
            else:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
        else:
            rate_details = ""

        # Cost-centre allocation block (mirrors PO / GRV / SO / OTC logic)
        _sinv_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch}</NAME>
                            <AMOUNT>{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        # AMOUNT positive, ISDEEMEDPOSITIVE=No — matches Sales_23.xml exactly.
        # VATASSBLVALUE = taxable line amount (needed for GST assessable value).
        # DESTINATIONGODOWNNAME required in BATCHALLOCATIONS for Sales Invoice.
        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>{amt:.2f}</AMOUNT>
                <VATASSBLVALUE>{amt:.2f}</VATASSBLVALUE>
                <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{line_wh}</DESTINATIONGODOWNNAME>
                    {f'<ORDERNO>{line_so}</ORDERNO>' if line_so else ''}
                    <ORDERDUEDATE>{t_date}</ORDERDUEDATE>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_SALES}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    {_sinv_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # GST ledger entries: slab-wise CGST+SGST (intra) or IGST (inter-state)
    # Amounts are POSITIVE, ISDEEMEDPOSITIVE=No (output tax liability)
    # Enrich lines: decode RBS_TAXCODE → MAHI_TAXRATE so _build_gst_groups catches it
    enriched_lines_sinv = []
    for _l in raw_lines:
        _e = dict(_l)
        if _e.get("MAHI_TAXRATE") is None and _e.get("RBS_TAXCODE") is not None:
            try:
                _e["MAHI_TAXRATE"] = _decode_mahi_taxrate(_e["RBS_TAXCODE"])
            except Exception:
                pass
        enriched_lines_sinv.append(_e)

    gst_groups_sinv = _build_gst_groups(enriched_lines_sinv, is_intrastate, gst_field="VAT", direction="output")
    # If no line-level MAHI_TAXRATE and no line VAT, fall back to header gst_total flat split
    if not gst_groups_sinv and gst_total > 0:
        if is_intrastate:
            cgst_amt = round(gst_total / 2, 2)
            gst_groups_sinv = {
                _gst_ledger_name("CGST", "9", "output"): cgst_amt,
                _gst_ledger_name("SGST", "9", "output"): round(gst_total - cgst_amt, 2),
            }
        else:
            gst_groups_sinv = {_gst_ledger_name("IGST", "18", "output"): gst_total}
    gst_entries = _gst_group_ledger_entries(
        gst_groups_sinv, is_intrastate, isdeemedpositive="No", sign=""
    )

    # Optional PARTYGSTIN tag (only if available)
    gstin_tag = f"<PARTYGSTIN>{party_gstin}</PARTYGSTIN>" if party_gstin else ""

    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <REFERENCE>{inv_no}</REFERENCE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>Maharashtra</STATENAME>
                        <PLACEOFSUPPLY>Maharashtra</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{customer}</PARTYLEDGERNAME>
                        <PARTYNAME>{customer}</PARTYNAME>
                        {gstin_tag}
                        <BASICORDERREF>{inv_no}</BASICORDERREF>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Sales Invoice from Priority ERP</NARRATION>
                        <ISINVOICE>Yes</ISINVOICE>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}

                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{customer}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                            <BILLALLOCATIONS.LIST>
                                <NAME>{inv_no}</NAME>
                                <BILLTYPE>New Ref</BILLTYPE>
                                <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                            </BILLALLOCATIONS.LIST>
                        </LEDGERENTRIES.LIST>{gst_entries}
                        {_order_list_blocks}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()

def run_sinv_push(invoices: list, dry_run: bool, source: str) -> list:
    """Push Final sales invoices to Tally as Sales Invoice vouchers (ISINVOICE=Yes)."""
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(invoices)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing customer ledgers & stock items in Tally…")
        for rec in invoices:
            c = rec.get("Cust. Name") or rec.get("CDES", "")
            if c: ensure_vendor_ledger(c, "Sundry Debtors")
            for line in rec.get(SINV_SUBFORM, []):
                ensure_stock_item(line.get("PARTNAME", ""), line.get("PDES", ""))
        status_ph.info("⚙ Step 2/2 — Pushing Sales Invoice vouchers to Tally…")
    for i, rec in enumerate(invoices):
        inv_no   = rec.get("Invoice No.") or rec.get("IVNUM", "?")
        status   = rec.get("Status") or rec.get("STATDES", "")
        customer = rec.get("Cust. Name") or rec.get("CDES", "")
        amount   = rec.get("Grand Total") or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{inv_no}` ({i+1}/{total})…")
        xml = build_sinv_xml(rec)
        if dry_run:
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Customer": customer, "Amount": fmt_inr(amount),
                            "Tally Type": "Sales (Invoice)", "Result": "🧪 Dry run — XML built, not pushed",
                            "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Customer": customer, "Amount": fmt_inr(amount),
                            "Tally Type": "Sales (Invoice)",
                            "Result": f"{'✅' if ok else '❌'} {msg}",
                            "XML": xml, "Tally Response": tally_raw,
                            "Timestamp": datetime.now().strftime("%H:%M:%S")})
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results

@st.cache_data(ttl=300, show_spinner=False)
def fetch_otc_sales_invoices():
    """Fetch OTC sales invoices from Priority EINVOICES with expanded line items.

    $select is required on both header and subform — Priority OData silently drops
    non-standard fields (MAHI_TAXRATE, RBS_TAXCODE, BRANCHNAME) unless explicitly
    requested.  Falls back to a bare $expand if $select is rejected.
    """
    hdrs = _auth_headers()
    otc_header_select = (
        "CUSTNAME,CDES,IVDATE,CURDATE,IVNUM,QPRICE,VAT,TOTPRICE,"
        "STATDES,WARHSNAME,PARTYVAT,STATENAME,TAXCODE,BRANCHNAME"
    )
    # MAHI_TAXRATE  = numeric GST % per line (e.g. 18)
    # RBS_TAXCODE   = VAT Group code per line (e.g. "018") — same as ORDERS subform
    # Both are needed: Priority may return one but not the other depending on version.
    otc_line_select = (
        "PARTNAME,PDES,TQUANT,TUNITNAME,PRICE,QPRICE,VAT,"
        "MAHI_TAXRATE,RBS_TAXCODE,WARHSNAME"
    )
    url_with_select = (
        f"{PRIORITY_BASE}/{OTC_FORM}"
        f"?$select={otc_header_select}"
        f"&$expand={OTC_SUBFORM}($select={otc_line_select})"
        f"&$count=true&$top=500"
    )
    url_bare = f"{PRIORITY_BASE}/{OTC_FORM}?$expand={OTC_SUBFORM}&$count=true&$top=500"

    for base_url in (url_with_select, url_bare):
        try:
            records = []
            expected_count = None
            url = base_url
            while url:
                resp = requests.get(url, headers=hdrs, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                if expected_count is None:
                    expected_count = data.get("@odata.count")
                records.extend(data.get("value", []))
                url = data.get("@odata.nextLink") or data.get("odata.nextLink") or data.get("nextLink")
            if records is not None:
                return records, expected_count
        except Exception:
            continue
    return [], None

def build_otc_header_df(raw):
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    if OTC_SUBFORM in df.columns:
        df = df.drop(columns=[OTC_SUBFORM])
    if "IVDATE" in df.columns and "CURDATE" in df.columns:
        df["IVDATE"] = df["IVDATE"].fillna(df["CURDATE"])
        df = df.drop(columns=["CURDATE"])
    df = df.rename(columns={k: v for k, v in OTC_HEADER_MAP.items() if k in df.columns})
    df = _parse_dates(df, "Date")
    return _to_num(df, "Taxable Total", "GST Amount", "Grand Total")

def build_otc_lines_df(raw):
    rows = []
    for inv in raw:
        lines = inv.get(OTC_SUBFORM, [])
        if not lines:
            continue
        base = {
            "Invoice No.": inv.get("IVNUM"),
            "Customer Name": inv.get("CDES"),
            "Date": inv.get("IVDATE") or inv.get("CURDATE"),
            "Status": inv.get("STATDES", ""),
            "Warehouse": inv.get("WARHSNAME", ""),
        }
        for line in lines:
            rows.append({**base, **{v: line.get(k) for k, v in OTC_LINE_MAP.items()}})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    return _to_num(df, "Quantity", "Unit Price", "Total Price", "Line GST", "GST Slab Rate")

def build_otc_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy()
        df["Line Count"] = 0
        df["Parts"] = ""
        df["Lines Total"] = 0.0
        return df
    agg = (
        lines_df.groupby("Invoice No.")
        .agg(
            LC=("Part Description", "count"),
            LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
            LT=("Total Price", "sum"),
        )
        .reset_index()
        .rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"})
    )
    merged = header_df.merge(agg, on="Invoice No.", how="left")
    merged["Line Count"] = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"] = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged

def build_otc_sinv_xml(inv: dict) -> str:
    """Build a Tally Sales invoice XML from a Priority EINVOICES OTC record."""
    inv_no = inv.get("Invoice No.") or inv.get("IVNUM", "")
    raw_date = inv.get("Date") or inv.get("IVDATE") or inv.get("CURDATE", "")
    customer = inv.get("Customer Name") or inv.get("CDES", "")
    warehouse = inv.get("Warehouse") or inv.get("WARHSNAME", "Main Location")
    branch    = str(inv.get("Branch") or inv.get("BRANCHNAME") or "").strip()
    grand_tot = float(inv.get("Grand Total") or inv.get("TOTPRICE") or 0)
    gst_total = float(inv.get("GST Amount") or inv.get("VAT") or 0)
    party_gstin = str(inv.get("Customer GSTIN") or inv.get("PARTYVAT") or inv.get("PARTYGSTIN") or "").strip()
    party_state = str(inv.get("Customer State") or inv.get("STATENAME") or COMPANY_STATE).strip() or COMPANY_STATE
    t_date = _tally_date(str(raw_date))

    inv_no_xml = _xml_text(inv_no)
    customer_xml = _xml_text(customer)
    party_state_xml = _xml_text(party_state)
    sales_ledger_xml = _xml_text(LEDGER_SALES)
    vch_type_xml = _xml_text(OTC_TALLY_VCH_TYPE)

    is_intrastate = _detect_intrastate(inv)
    raw_lines = inv.get(OTC_SUBFORM) or []

    inv_entries = ""
    for line in raw_lines:
        pn = str(line.get("PARTNAME") or line.get("Part Number", "")).strip()
        pd_ = str(line.get("PDES") or line.get("Part Description", "")).strip()
        name = resolve_po_item_name(pn, pd_)
        if not name:
            continue
        try:
            qty = float(line.get("TQUANT") or line.get("Quantity", 0))
            rate = float(line.get("PRICE") or line.get("Unit Price", 0))
            amt = float(line.get("QPRICE") or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        raw_unit = str(line.get("TUNITNAME") or line.get("Unit", "")).strip()
        unit = raw_unit if raw_unit else _resolve_unit(name)
        line_wh = str(line.get("WARHSNAME") or line.get("Warehouse") or warehouse or "Main Location").strip() or "Main Location"

        # GST % resolution — three-tier chain matching Sales Order / Multi Shipment:
        # 1. MAHI_TAXRATE — numeric % direct (e.g. 18); most reliable when present.
        # 2. RBS_TAXCODE  — VAT Group code (e.g. "018"); same field used by ORDERS subform.
        # 3. Line VAT rupee amount → back-calculate %; proportional header fallback last.
        raw_taxrate = line.get("MAHI_TAXRATE")
        raw_rbs     = line.get("RBS_TAXCODE")
        total_gst_pct = 0.0
        if raw_taxrate is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(raw_taxrate)
            except Exception:
                total_gst_pct = 0.0
        if total_gst_pct == 0.0 and raw_rbs is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(raw_rbs)
            except Exception:
                total_gst_pct = 0.0
        if total_gst_pct == 0.0:
            try:
                line_vat = float(line.get("VAT") or line.get("Line GST") or 0)
            except Exception:
                line_vat = 0.0
            if line_vat <= 0 and amt > 0 and gst_total > 0:
                total_line_amt = sum(float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines) or 1.0
                line_vat = round(gst_total * (amt / total_line_amt), 2)
            total_gst_pct = round(line_vat / amt * 100, 2) if amt > 0 and line_vat > 0 else 0.0

        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        if total_gst_pct > 0:
            if is_intrastate:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
            else:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
        else:
            rate_details = ""

        name_xml = _xml_text(name)
        unit_xml = _xml_text(unit)
        line_wh_xml = _xml_text(line_wh)
        branch_xml = _xml_text(branch)

        _otc_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch_xml}</NAME>
                            <AMOUNT>{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name_xml}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit_xml}</RATE>
                <AMOUNT>{amt:.2f}</AMOUNT>
                <VATASSBLVALUE>{amt:.2f}</VATASSBLVALUE>
                <ACTUALQTY>{qty:.4f} {unit_xml}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit_xml}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh_xml}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{line_wh_xml}</DESTINATIONGODOWNNAME>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit_xml}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit_xml}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{sales_ledger_xml}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    {_otc_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # Enrich lines: if MAHI_TAXRATE absent but RBS_TAXCODE present, decode it so
    # _build_gst_groups can compute slab-wise rupee amounts correctly.
    enriched_lines_otc = []
    for _l in raw_lines:
        _e = dict(_l)
        if _e.get("MAHI_TAXRATE") is None and _e.get("RBS_TAXCODE") is not None:
            try:
                _e["MAHI_TAXRATE"] = _decode_mahi_taxrate(_e["RBS_TAXCODE"])
            except Exception:
                pass
        enriched_lines_otc.append(_e)

    gst_groups_otc = _build_gst_groups(enriched_lines_otc, is_intrastate, gst_field="VAT", direction="output")
    if not gst_groups_otc and gst_total > 0:
        if is_intrastate:
            cgst_amt = round(gst_total / 2, 2)
            gst_groups_otc = {
                _gst_ledger_name("CGST", "9", "output"): cgst_amt,
                _gst_ledger_name("SGST", "9", "output"): round(gst_total - cgst_amt, 2),
            }
        else:
            gst_groups_otc = {_gst_ledger_name("IGST", "18", "output"): gst_total}
    gst_entries = _gst_group_ledger_entries(
        gst_groups_otc, is_intrastate, isdeemedpositive="No", sign=""
    )

    gstin_tag = f"<PARTYGSTIN>{_xml_text(party_gstin)}</PARTYGSTIN>" if party_gstin else ""

    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="{OTC_TALLY_VCH_TYPE}" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>{vch_type_xml}</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no_xml}</VOUCHERNUMBER>
                        <REFERENCE>{inv_no_xml}</REFERENCE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>{party_state_xml}</STATENAME>
                        <PLACEOFSUPPLY>{party_state_xml}</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{customer_xml}</PARTYLEDGERNAME>
                        <PARTYNAME>{customer_xml}</PARTYNAME>
                        {gstin_tag}
                        <BASICORDERREF>{inv_no_xml}</BASICORDERREF>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final OTC Sales Invoice from Priority ERP</NARRATION>
                        <ISINVOICE>Yes</ISINVOICE>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{_xml_text(branch)}</COSTCENTRENAME>' if branch else ''}

                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{customer_xml}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                            <BILLALLOCATIONS.LIST>
                                <NAME>{inv_no_xml}</NAME>
                                <BILLTYPE>New Ref</BILLTYPE>
                                <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                            </BILLALLOCATIONS.LIST>
                        </LEDGERENTRIES.LIST>{gst_entries}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()

def run_otc_push(invoices: list, dry_run: bool, source: str) -> list:
    """Push Final OTC sales invoices to Tally as Sales vouchers (ISINVOICE=Yes)."""
    results = []
    total = len(invoices)
    prog = st.progress(0)
    status_ph = st.empty()
    if total == 0:
        prog.empty()
        status_ph.empty()
        return results

    if not dry_run:
        status_ph.info("Step 1/2 - Creating missing OTC customer ledgers & stock items in Tally...")
        for rec in invoices:
            c = rec.get("Customer Name") or rec.get("CDES", "")
            if c:
                ensure_vendor_ledger(c, "Sundry Debtors")
            is_intra = _detect_intrastate(rec)
            for line in rec.get(OTC_SUBFORM, []):
                item_name = resolve_po_item_name(line.get("PARTNAME", ""), line.get("PDES", ""))
                if not item_name:
                    continue
                gst_rate = _decode_mahi_taxrate(line.get("MAHI_TAXRATE"))
                ensure_stock_item(item_name, "", gst_rate=gst_rate, is_intrastate=is_intra)
        status_ph.info("Step 2/2 - Pushing OTC Sales Invoice vouchers to Tally...")

    for i, rec in enumerate(invoices):
        inv_no = rec.get("Invoice No.") or rec.get("IVNUM", "?")
        status = rec.get("Status") or rec.get("STATDES", "")
        customer = rec.get("Customer Name") or rec.get("CDES", "")
        amount = rec.get("Grand Total") or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{inv_no}` ({i + 1}/{total})...")
        try:
            xml = build_otc_sinv_xml(rec)
            if dry_run:
                results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                                "Customer": customer, "Amount": fmt_inr(amount),
                                "Tally Type": "OTC Sales (Invoice)",
                                "Result": "Dry run - XML built, not pushed",
                                "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
            else:
                ok, msg, tally_raw = push_to_tally(xml)
                results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                                "Customer": customer, "Amount": fmt_inr(amount),
                                "Tally Type": "OTC Sales (Invoice)",
                                "Result": f"{'OK' if ok else 'ERROR'} {msg}",
                                "XML": xml, "Tally Response": tally_raw,
                                "Timestamp": datetime.now().strftime("%H:%M:%S")})
                time.sleep(0.25)
        except Exception as e:
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Customer": customer, "Amount": fmt_inr(amount),
                            "Tally Type": "OTC Sales (Invoice)",
                            "Result": f"ERROR XML build failed: {e}",
                            "XML": "", "Timestamp": datetime.now().strftime("%H:%M:%S")})
        prog.progress((i + 1) / total)
    prog.empty()
    status_ph.empty()
    return results

# ─── MASTER PROVISIONING ──────────────────────────────────────────────────────
def ensure_vendor_ledger(name: str, parent_type: str = "Sundry Creditors") -> str:
    if not name: return "error: empty name"
    xml = f"""<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME><STATICVARIABLES><SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="{name}" ACTION="Create"><NAME>{name}</NAME><PARENT>{parent_type}</PARENT><ISBILLWISEON>Yes</ISBILLWISEON><AFFECTSSTOCK>No</AFFECTSSTOCK></LEDGER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""
    try:
        requests.post(TALLY_URL, data=xml.encode("utf-8"), headers={"Content-Type": "application/xml"}, timeout=5)
        return "created/exists"
    except: return "error"

def _tally_stock_item_exists(name: str) -> bool:
    """
    Ask Tally whether a stock item with this exact name already exists.
    Uses an Export request; returns True if the item is found in the response.
    """
    xml = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>List of Accounts</REPORTNAME>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      <ACCOUNTTYPE>Stock Items</ACCOUNTTYPE>
    </STATICVARIABLES>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
    try:
        resp = requests.post(TALLY_URL, data=xml.encode("utf-8"),
                             headers={"Content-Type": "application/xml"}, timeout=8)
        if resp.status_code == 200:
            # Case-insensitive search for the item name tag
            return bool(re.search(
                rf"<NAME>\s*{re.escape(name)}\s*</NAME>",
                resp.text, re.I
            ))
    except Exception:
        pass
    return False


# Prefix → Tally stock group mapping.
# Extend this dict to cover your naming conventions.
_STOCK_GROUP_PREFIX_MAP = {
    "FG-":   "Finished Goods",
    "RM-":   "Raw Materials",
    "PKG-":  "Packing Materials",
    "WIP-":  "Work In Progress",
    "SFG-":  "Semi-Finished Goods",
    "CONS-": "Consumables",
    "SERV-": "Services",
}

def _resolve_stock_group(item_name: str) -> str:
    """Return the best Tally stock group for an item based on its name prefix."""
    upper = item_name.upper()
    for prefix, group in _STOCK_GROUP_PREFIX_MAP.items():
        if upper.startswith(prefix):
            return group
    return "Raw Materials"   # safe default for unrecognised items


def ensure_stock_item(code, desc, gst_rate: float = 0.0, is_intrastate: bool = True) -> tuple[str, str]:
    """
    Ensure a stock item exists in Tally, with its GST rate set on the master.

    CRITICAL: Tally cross-checks voucher GST amounts against the GST rate stored
    on the stock item MASTER. If the master has no rate (0%) but the voucher sends
    IGST/CGST/SGST, Tally fires "Tax amount does not match calculated value" warning.
    Setting the rate here on the master eliminates that warning permanently.

    1. Resolve the display name from code / description.
    2. Check if the item already exists in Tally — if yes, SKIP (preserve manual GST setup).
    3. If missing, create it under the correct group with the GST rate set.

    NOTE: Existing items are never modified. Any GST details (HSN, rate, classification)
    set manually in Tally are left untouched.
    """
    name = resolve_po_item_name(code, desc)
    if not name:
        return "", "error: empty name"

    # ── If item already exists, do NOT overwrite it ───────────────────────────
    # Tally's ACTION="Create" on an existing master acts as an alter and
    # resets manually configured GST details (HSN code, tax classification, etc.).
    if _tally_stock_item_exists(name):
        return name, "exists (skipped — manual GST details preserved)"

    parent = _resolve_stock_group(name)

    # Build GST rate details for the stock item master.
    # Tally needs CGST+SGST (intra) or IGST (inter) set on the item.
    gst_master_xml = ""
    if gst_rate > 0:
        if is_intrastate:
            half = round(gst_rate / 2, 4)
            gst_master_xml = (
                f"<GSTDETAILS.LIST>"
                f"<APPLICABLEFROM>20000401</APPLICABLEFROM>"
                f"<CALCULATIONTYPE>On Value</CALCULATIONTYPE>"
                f"<HSNMASTERNAME></HSNMASTERNAME>"
                f"<TAXABILITY>Taxable</TAXABILITY>"
                f"<CGSTRATE>{half}</CGSTRATE>"
                f"<SGSTRATE>{half}</SGSTRATE>"
                f"<IGSTRATE>{gst_rate}</IGSTRATE>"
                f"<UTGSTRATE>0</UTGSTRATE>"
                f"<CESSRATE>0</CESSRATE>"
                f"</GSTDETAILS.LIST>"
            )
        else:
            gst_master_xml = (
                f"<GSTDETAILS.LIST>"
                f"<APPLICABLEFROM>20000401</APPLICABLEFROM>"
                f"<CALCULATIONTYPE>On Value</CALCULATIONTYPE>"
                f"<HSNMASTERNAME></HSNMASTERNAME>"
                f"<TAXABILITY>Taxable</TAXABILITY>"
                f"<CGSTRATE>{round(gst_rate/2, 4)}</CGSTRATE>"
                f"<SGSTRATE>{round(gst_rate/2, 4)}</SGSTRATE>"
                f"<IGSTRATE>{gst_rate}</IGSTRATE>"
                f"<UTGSTRATE>0</UTGSTRATE>"
                f"<CESSRATE>0</CESSRATE>"
                f"</GSTDETAILS.LIST>"
            )
    else:
        # Explicitly exempt
        gst_master_xml = (
            f"<GSTDETAILS.LIST>"
            f"<APPLICABLEFROM>20000401</APPLICABLEFROM>"
            f"<CALCULATIONTYPE>On Value</CALCULATIONTYPE>"
            f"<TAXABILITY>Exempt</TAXABILITY>"
            f"<CGSTRATE>0</CGSTRATE><SGSTRATE>0</SGSTRATE>"
            f"<IGSTRATE>0</IGSTRATE><UTGSTRATE>0</UTGSTRATE><CESSRATE>0</CESSRATE>"
            f"</GSTDETAILS.LIST>"
        )

    # Use ACTION="Create" — Tally treats this as create-or-alter (idempotent)
    xml = (
        f"""<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>"""
        f"""<BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME>"""
        f"""<STATICVARIABLES><SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>"""
        f"""</STATICVARIABLES></REQUESTDESC><REQUESTDATA>"""
        f"""<TALLYMESSAGE xmlns:UDF="TallyUDF">"""
        f"""<STOCKITEM NAME="{name}" ACTION="Create">"""
        f"""<NAME>{name}</NAME><PARENT>{parent}</PARENT>"""
        f"""{gst_master_xml}"""
        f"""</STOCKITEM></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""
    )
    try:
        requests.post(TALLY_URL, data=xml.encode("utf-8"),
                      headers={"Content-Type": "application/xml"}, timeout=5)
        if _tally_stock_item_exists(name):
            return name, f"created under {parent} @ {gst_rate}% GST"
        return name, f"created under {parent}"
    except Exception:
        return name, "error: gateway unreachable"

# ─── TALLY PUSH ───────────────────────────────────────────────────────────────
def push_to_tally(xml: str) -> tuple[bool, str, str]:
    """
    Push XML to Tally and correctly interpret the response.

    Tally ALWAYS returns HTTP 200 even on failure — never trust the status code alone.
    The actual result is encoded in the response body tags:

      <CREATED>N</CREATED>     N>=1 = success, N=0 = silent rejection
      <EXCEPTIONS>N</EXCEPTIONS>  N>=1 = voucher type/structure mismatch
                                         (e.g. LEDGERENTRIES used instead of
                                          ALLLEDGERENTRIES on ISINVOICE=Yes)
      <LINEERROR>msg</LINEERROR>   explicit validation error from Tally
      <ERRORS>N</ERRORS>           error count
    """
    try:
        resp = requests.post(TALLY_URL, data=xml.encode("utf-8"),
                             headers={"Content-Type": "application/xml"}, timeout=30)
        raw = resp.text

        if resp.status_code != 200:
            return False, f"HTTP Error {resp.status_code}", raw

        # Explicit line-level validation error
        if "LINEERROR" in raw.upper():
            err = re.search(r"<LINEERROR>(.*?)</LINEERROR>", raw, re.I | re.S)
            msg = err.group(1).strip() if err else "Validation failed"
            return False, f"Tally LINEERROR: {msg}", raw

        # EXCEPTIONS = voucher structure/type mismatch
        # Fixed: build_sinv_xml now correctly uses LEDGERENTRIES.LIST (not ALLLEDGERENTRIES.LIST)
        # as confirmed by real Tally Sales Invoice XML export.
        exc_match = re.search(r"<EXCEPTIONS>\s*(\d+)\s*</EXCEPTIONS>", raw, re.I)
        if exc_match and int(exc_match.group(1)) > 0:
            return False, f"Tally EXCEPTIONS={exc_match.group(1)} — voucher structure mismatch (XML tag or ledger issue)", raw

        # CREATED count — definitive success/failure indicator
        created_match = re.search(r"<CREATED>\s*(\d+)\s*</CREATED>", raw, re.I)
        if created_match:
            n = int(created_match.group(1))
            if n == 0:
                return False, "Tally CREATED=0 — voucher rejected (ledger/stock item missing or entry imbalance)", raw
            return True, f"Created in Tally Day Book ✓ (CREATED={n})", raw

        # Fallback if no CREATED tag (older Tally versions)
        return True, "Pushed to Tally (response unverified)", raw

    except requests.exceptions.ConnectionError:
        return False, "Connection refused — is Tally open and Gateway running on port 9000?", ""
    except requests.exceptions.Timeout:
        return False, "Tally Gateway timed out — is TallyPrime open?", ""
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", ""

# ─── DATA FETCH ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_orders():
    # No $select — bare $expand so Priority returns ALL fields including BRANCHNAME.
    # Using $select would silently drop any field not explicitly listed.
    hdrs = _auth_headers()
    try:
        records = _paginate(f"{PRIORITY_BASE}/PORDERS?$expand={SUBFORM_NAV}&$top=500", hdrs)
        return records, any(isinstance(r.get(SUBFORM_NAV), list) and len(r.get(SUBFORM_NAV, [])) > 0 for r in records)
    except Exception:
        return [], False

@st.cache_data(ttl=300, show_spinner=False)
def fetch_sales_orders():
    hdrs = _auth_headers()
    so_header_select = (
        "CUSTNAME,CDES,CURDATE,ORDNAME,QPRICE,PERCENT,DISPRICE,"
        "TOTPRICE,VAT,CODE,ORDSTATUSDES,STATDES,STAT,WARHSNAME,BRANCHNAME"
    )
    url = (f"{PRIORITY_BASE}/ORDERS"
           f"?$select={so_header_select}"
           f"&$expand={SO_SUBFORM_NAV}"
           f"&$top=500")
    try:
        records = _paginate(url, hdrs)
        return records, any(isinstance(r.get(SO_SUBFORM_NAV), list) and len(r.get(SO_SUBFORM_NAV, [])) > 0 for r in records)
    except Exception:
        try:
            fallback = _paginate(f"{PRIORITY_BASE}/ORDERS?$expand={SO_SUBFORM_NAV}&$top=500", hdrs)
            return fallback, False
        except Exception:
            return [], False

# ─── DATAFRAME BUILDERS ───────────────────────────────────────────────────────
def build_header_df(raw):
    df = pd.DataFrame(raw)
    if SUBFORM_NAV in df.columns: df = df.drop(columns=[SUBFORM_NAV])
    df = df.rename(columns={k: v for k, v in HEADER_FIELD_MAP.items() if k in df.columns})
    if "Status" not in df.columns and "_STAT_CODE" in df.columns:
        df["Status"] = df["_STAT_CODE"].map(STATUS_MAP_FALLBACK).fillna(df["_STAT_CODE"])
    df = df.drop(columns=["_STAT_CODE"], errors="ignore")
    return _to_num(_parse_dates(df, "Date"), "Total Cost (INR)", "VAT")

def build_lines_df(raw):
    rows = []
    for order in raw:
        lines = order.get(SUBFORM_NAV, [])
        if not lines: continue
        base = {"Order": order.get("ORDNAME"), "Vendor Name": order.get("CDES"),
                "Date": order.get("CURDATE"), "Warehouse": order.get("WARHSNAME"),
                "Header Status": order.get("STATDES") or STATUS_MAP_FALLBACK.get(order.get("STAT", ""), order.get("STAT", ""))}
        for line in lines:
            row = {**base, **{v: line.get(k) for k, v in SUBFORM_FIELD_MAP.items()}}
            rows.append(row)
    if not rows: return pd.DataFrame()
    return _to_num(_parse_dates(pd.DataFrame(rows), "Date", "Due Date"), "Quantity", "Unit Price", "Discount %", "Total Price", "GST")

def build_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy(); df["Line Count"] = 0; df["Parts"] = ""; df["Lines Total"] = 0.0
        return df
    agg = (lines_df.groupby("Order")
           .agg(LC=("Part Description", "count"),
                LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
                LT=("Total Price", "sum"))
           .reset_index().rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"}))
    merged = header_df.merge(agg, on="Order", how="left")
    merged["Line Count"]  = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"]       = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged


# ─── PUSH ENGINES ─────────────────────────────────────────────────────────────
def run_po_push(orders: list, dry_run: bool, source: str) -> list:
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(orders)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing vendor ledgers & stock items in Tally…")
        for rec in orders:
            v = rec.get("Vendor Name") or rec.get("CDES", "")
            if v: ensure_vendor_ledger(v, "Sundry Creditors")
            for line in rec.get(SUBFORM_NAV, []):
                # Pass PARTNAME as 'code' and PDES as 'desc'.
                # ensure_stock_item internally calls resolve_po_item_name so PARTNAME wins.
                partname = line.get("PARTNAME", "")
                pdes     = line.get("PDES", "")
                # Use PO-specific resolver: prefer PARTNAME (RM-CurryLeaf) over PDES (Curry Leaf)
                item_name = resolve_po_item_name(partname, pdes)
                if item_name:
                    ensure_stock_item(item_name, "")   # pass resolved name directly as code
        status_ph.info("⚙ Step 2/2 — Pushing Purchase Order vouchers to Tally Day Book…")
    for i, rec in enumerate(orders):
        ord_no   = rec.get("Order") or rec.get("ORDNAME", "?")
        status   = rec.get("Status") or rec.get("STATDES", "")
        supplier = rec.get("Vendor Name") or rec.get("CDES", "")
        amount   = rec.get("Total Cost (INR)") or rec.get("MAINDISPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{ord_no}` ({i+1}/{total})…")
        xml = build_voucher_xml(rec)
        if dry_run:
            results.append({"Source": source, "Order No": ord_no, "Status": status,
                            "Supplier/Customer": supplier, "Amount": fmt_inr(amount),
                            "Tally Type": "Purchase Order", "Result": "🧪 Dry run — XML built, not pushed",
                            "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({"Source": source, "Order No": ord_no, "Status": status,
                            "Supplier/Customer": supplier, "Amount": fmt_inr(amount),
                            "Tally Type": "Purchase Order",
                            "Result": f"{'✅' if ok else '❌'} {msg}",
                            "XML": xml, "Tally Response": tally_raw,
                            "Timestamp": datetime.now().strftime("%H:%M:%S")})
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results

def run_so_push(orders: list, dry_run: bool, source: str) -> list:
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(orders)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing customer ledgers & stock items in Tally…")
        for rec in orders:
            c = rec.get("Cust. Name") or rec.get("CDES", "")
            if c: ensure_vendor_ledger(c, "Sundry Debtors")
            for line in rec.get(SO_SUBFORM_NAV, []):
                so_item = resolve_po_item_name(line.get("PARTNAME", ""), line.get("PDES", ""))
                if so_item:
                    ensure_stock_item(so_item, "")
        status_ph.info("⚙ Step 2/2 — Pushing Sales Order vouchers to Tally Day Book…")
    for i, rec in enumerate(orders):
        ord_no   = rec.get("Order No.") or rec.get("ORDNAME", "?")
        status   = rec.get("Status") or rec.get("STATDES", "")
        customer = rec.get("Cust. Name") or rec.get("CDES", "")
        amount   = rec.get("Final Price") or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{ord_no}` ({i+1}/{total})…")
        xml = build_so_voucher_xml(rec)
        if dry_run:
            results.append({"Source": source, "Order No": ord_no, "Status": status,
                            "Supplier/Customer": customer, "Amount": fmt_inr(amount),
                            "Tally Type": "Sales Order", "Result": "🧪 Dry run — XML built, not pushed",
                            "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({"Source": source, "Order No": ord_no, "Status": status,
                            "Supplier/Customer": customer, "Amount": fmt_inr(amount),
                            "Tally Type": "Sales Order",
                            "Result": f"{'✅' if ok else '❌'} {msg}",
                            "XML": xml, "Tally Response": tally_raw,
                            "Timestamp": datetime.now().strftime("%H:%M:%S")})
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results

def query_daybook_by_type(vch_type: str) -> set:
    """
    Query Tally for all voucher numbers of a given type.

    Strategy: use TWO queries and union the results:
      1. Day Book (date-scoped, fast — catches today's entries)
      2. Voucher Collection via TDL Export (all-dates — catches historical entries)

    Receipt Notes, Purchase Orders, Sales Orders are NOT in the Day Book
    by default in some Tally configurations — the Collection query covers them.
    """
    nos = set()

    # ── Query 1: Day Book (current Tally date range) ─────────────────────────
    daybook_xml = f"""<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>Day Book</REPORTNAME><STATICVARIABLES><SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"""
    try:
        resp = requests.post(TALLY_URL, data=daybook_xml.encode("utf-8"),
                             headers={"Content-Type": "application/xml"}, timeout=6)
        if resp.status_code == 200:
            _extract_vch_nos(resp.text, vch_type, nos)
    except Exception:
        pass

    # ── Query 2: All-dates Collection export (Voucher Register style) ─────────
    # Uses TDL COLLECTION to scan ALL vouchers of the given type regardless of
    # the current Tally date period.  This is the correct way to detect
    # Receipt Notes, Purchase Orders and any voucher type that the Day Book
    # may miss due to date-period scoping.
    collection_xml = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>List of Vouchers</REPORTNAME>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      <SVFROMDATE>19000101</SVFROMDATE>
      <SVTODATE>21001231</SVTODATE>
    </STATICVARIABLES>
    <TDL><TDLMESSAGE>
      <REPORT NAME="List of Vouchers">
        <FORMS>List of Vouchers</FORMS>
      </REPORT>
      <FORM NAME="List of Vouchers">
        <TOPPARTS>List of Vouchers</TOPPARTS>
        <XMLTAG>LISTOFVOUCHERS</XMLTAG>
      </FORM>
      <PART NAME="List of Vouchers">
        <TOPLINES>List of Vouchers</TOPLINES>
        <REPEAT>List of Vouchers : VchCollection</REPEAT>
        <SCROLLED>Vertical</SCROLLED>
      </PART>
      <LINE NAME="List of Vouchers">
        <FIELDS>FldVchType,FldVchNo,FldVchRef</FIELDS>
      </LINE>
      <FIELD NAME="FldVchType"><SET>$VoucherTypeName</SET><XMLTAG>VOUCHERTYPENAME</XMLTAG></FIELD>
      <FIELD NAME="FldVchNo"><SET>$VoucherNumber</SET><XMLTAG>VOUCHERNUMBER</XMLTAG></FIELD>
      <FIELD NAME="FldVchRef"><SET>$Reference</SET><XMLTAG>REFERENCE</XMLTAG></FIELD>
      <COLLECTION NAME="VchCollection">
        <TYPE>Vouchers</TYPE>
        <FILTERS>FilterByType</FILTERS>
      </COLLECTION>
      <SYSTEM TYPE="Formulae" NAME="FilterByType">
        $VoucherTypeName = "{vch_type}"
      </SYSTEM>
    </TDLMESSAGE></TDL>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
    try:
        resp2 = requests.post(TALLY_URL, data=collection_xml.encode("utf-8"),
                              headers={"Content-Type": "application/xml"}, timeout=10)
        if resp2.status_code == 200:
            _extract_vch_nos(resp2.text, vch_type, nos)
    except Exception:
        pass

    return nos


def _extract_vch_nos(xml_text: str, vch_type: str, nos: set) -> None:
    """
    Extract voucher numbers + references from a Tally XML response into `nos`.
    Handles both cases:
      • VOUCHERTYPENAME appears BEFORE VOUCHERNUMBER/REFERENCE  (Day Book style)
      • Stand-alone VOUCHERNUMBER tags in TDL Collection export
    """
    # Pattern 1: type tag before number/reference tag (Day Book, Collection)
    pat = re.escape(vch_type)
    for m in re.finditer(
        rf"<VOUCHERTYPENAME>\s*{pat}\s*</VOUCHERTYPENAME>.*?<VOUCHERNUMBER>(.*?)</VOUCHERNUMBER>",
        xml_text, re.I | re.S
    ):
        v = m.group(1).strip()
        if v:
            nos.add(v)
    for m in re.finditer(
        rf"<VOUCHERTYPENAME>\s*{pat}\s*</VOUCHERTYPENAME>.*?<REFERENCE>(.*?)</REFERENCE>",
        xml_text, re.I | re.S
    ):
        v = m.group(1).strip()
        if v:
            nos.add(v)

    # Pattern 2: bare VOUCHERNUMBER without preceding type tag (some TDL exports)
    # Only add if VOUCHERTYPENAME appears anywhere in the same block
    blocks = re.findall(
        r"<VOUCHERNUMBER>(.*?)</VOUCHERNUMBER>",
        xml_text, re.I | re.S
    )
    if vch_type.lower() in xml_text.lower() and blocks:
        # Only trust bare numbers when the overall response is type-filtered
        # (i.e., Collection XML where ALL returned entries are of the given type)
        if "<LISTOFVOUCHERS>" in xml_text.upper() or "VchCollection" in xml_text:
            for v in blocks:
                v = v.strip()
                if v:
                    nos.add(v)

def render_push_results(results: list, dry_run: bool):
    st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
    df = pd.DataFrame(results)
    cols = ["Order No", "Supplier/Customer", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    ok_n  = sum(1 for r in results if "✅" in str(r.get("Result", "")))
    err_n = sum(1 for r in results if "❌" in str(r.get("Result", "")))
    if dry_run:
        st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
    elif ok_n:
        st.markdown(f'<div class="alert alert-success">✅ {ok_n} voucher(s) created. {err_n} error(s).</div>', unsafe_allow_html=True)
    if "push_log" not in st.session_state: st.session_state.push_log = []
    st.session_state.push_log.extend(results)

# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE: ENTRY JOURNAL  (FNCTRANS — Posted → Tally Journal Voucher)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── ENTRY JOURNAL CONFIG ────────────────────────────────────────────────────────────
JRNL_FORM        = "FNCTRANS"
JRNL_SUBFORM     = "FNCITEMS_SUBFORM"   # Priority OData nav property always uses _SUBFORM suffix
JRNL_PUSH_STATUS = "Y"   # Posted? field = Y means posted

JRNL_HEADER_MAP = {
    "TRANSCPTNTH": "Internal No.",
    "FNCNUM":      "Entry No.",          # Priority journal/voucher number → Tally VOUCHERNUMBER
    "TRANSDATE":   "Date",
    "BALDATE":     "Transaction Date",   # value date → Tally DATE
    "FNCREF":      "Reference",          # journal reference → Tally REFERENCE
    "REFERENCE":   "Reference",          # fallback alias
    "REFERENCE2":  "Reference 2",
    "DETAILS":     "Details",
    "BRANCHNAME":  "Branch / Cost Centre",  # cost centre → Tally COSTCENTRENAME
    "DEBITACC":    "Debit Account",
    "CDES":        "Debit Account Desc",
    "CREDITACC":   "Credit Account",
    "CDES2":       "Credit Account Desc",
    "QPRICE":      "Amount",
    "USDPRICE":    "Amount (USD)",
    "STATDES":     "Transaction Type",
    "POSTED":      "Posted",
    "CURDATE":     "Activity Date",
    "BATCHNUM":    "Batch Number",
}

JRNL_LINE_MAP = {
    "ACCNAME":   "Account No.",
    "ACCDES":    "Account Description",
    "DEBIT1":    "Debit",          # Priority field for debit amount in subform
    "CREDIT1":   "Credit",         # Priority field for credit amount in subform
    "DEBIT":     "Debit_fallback", # older alias kept for safety
    "CREDIT":    "Credit_fallback",
    "BALANCE":   "Balance",
    "DETAILS":   "Line Details",
    "DUEDATE":   "Due Date",
    "DEBITAMT":  "Debit (Trans. Curr)",
    "CREDITAMT": "Credit (Trans. Curr)",
}

# ─── ENTRY JOURNAL FETCH & BUILD ────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_fnctrans():
    hdrs = _auth_headers()
    url  = f"{PRIORITY_BASE}/{JRNL_FORM}?$expand={JRNL_SUBFORM}&$top=500"
    try:
        records   = _paginate(url, hdrs)
        has_lines = any(
            isinstance(r.get(JRNL_SUBFORM), list) and len(r[JRNL_SUBFORM]) > 0
            for r in records
        )
        return records, has_lines
    except Exception:
        try:
            fb = _paginate(f"{PRIORITY_BASE}/{JRNL_FORM}?$top=500", hdrs)
            return fb, False
        except Exception:
            return [], False


def build_jrnl_header_df(raw):
    df = pd.DataFrame(raw)
    if JRNL_SUBFORM in df.columns:
        df = df.drop(columns=[JRNL_SUBFORM])
    # FNCREF is the real reference field; drop the generic REFERENCE col if both exist to avoid duplicate
    if "FNCREF" in df.columns and "REFERENCE" in df.columns:
        df = df.drop(columns=["REFERENCE"])
    rename_map = {k: v for k, v in JRNL_HEADER_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)
    # Deduplicate any remaining duplicate column names (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]
    df = _parse_dates(df, "Date")
    df = _parse_dates(df, "Transaction Date")
    df = _to_num(df, "Amount")
    return df


def build_jrnl_lines_df(raw):
    rows = []
    for rec in raw:
        lines = rec.get(JRNL_SUBFORM, [])
        if not lines:
            continue
        base = {
            "Entry No.": rec.get("FNCNUM") or rec.get("TRANSCPTNTH"),  # FNCNUM is now the user-visible Entry No.
            "Date":      rec.get("BALDATE") or rec.get("TRANSDATE"),
            "Reference": rec.get("FNCREF") or rec.get("REFERENCE", ""),
            "Posted":    rec.get("POSTED", ""),
        }
        for line in lines:
            row = {**base, **{v: line.get(k) for k, v in JRNL_LINE_MAP.items() if k in line}}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Debit", "Credit", "Balance")
    return df


def build_jrnl_merged_df(header_df, lines_df, raw=None):
    """Merge header with aggregated line counts.
    If lines_df is empty (FNCITEMS_SUBFORM not expanding), derive line count
    directly from the raw records to show the true subform count.
    """
    df = header_df.copy()
    has_entry_col = "Entry No." in df.columns
    try:
        if not lines_df.empty and "Entry No." in lines_df.columns and "Account Description" in lines_df.columns:
            agg = (
                lines_df.groupby("Entry No.")
                .agg(
                    LC=("Account Description", "count"),
                    AC=("Account Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
                )
                .reset_index()
                .rename(columns={"LC": "Line Count", "AC": "Accounts"})
            )
            if has_entry_col:
                df = df.merge(agg, on="Entry No.", how="left")
            df["Line Count"] = df["Line Count"].fillna(0).astype(int) if "Line Count" in df.columns else 0
            df["Accounts"]   = df["Accounts"].fillna("") if "Accounts" in df.columns else ""
        elif raw and has_entry_col:
            lc_map = {
                str(rec.get("FNCNUM") or rec.get("TRANSCPTNTH", "")): len(rec.get(JRNL_SUBFORM, []))
                for rec in raw
            }
            df["Line Count"] = df["Entry No."].astype(str).map(lc_map).fillna(0).astype(int)
            df["Accounts"]   = ""
        else:
            df["Line Count"] = 0
            df["Accounts"]   = ""
    except Exception:
        df["Line Count"] = 0
        df["Accounts"]   = ""
    return df


JRNL_TALLY_VCH_TYPE = "Journal"


def build_jrnl_xml(rec: dict) -> str:
    """
    Build a Tally Journal Voucher XML from a Priority FNCTRANS record.

    Field mapping (Priority → Tally):
      BALDATE      → <DATE> + <REFERENCEDATE>  (both pushed if present; TRANSDATE fallback; omitted if both empty)
      FNCNUM       → <VOUCHERNUMBER>     (Priority journal number)
      FNCREF       → <REFERENCE>         (only pushed if FNCREF has a value; empty otherwise)
      BRANCHNAME   → <COSTCENTRENAME>    (voucher-level cost centre)
      FNCITEMS subform lines:
        ACCDES     → <LEDGERNAME>        (account description = ledger name in Tally)
        DEBIT1 > 0 → ISDEEMEDPOSITIVE=Yes, AMOUNT = -(DEBIT1)
        CREDIT1> 0 → ISDEEMEDPOSITIVE=No,  AMOUNT = +(CREDIT1)
        BRANCHNAME → COSTCENTREALLOCATIONS.LIST > NAME (per-line cost centre)

    Fallback when no FNCITEMS lines: use header DEBITACC/CREDITACC + QPRICE as 2-leg entry.

    Tally Journal sign convention (ISINVOICE=No):
      Debit  leg → ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (e.g. -500.00)
      Credit leg → ISDEEMEDPOSITIVE=No,  AMOUNT positive  (e.g. +500.00)
    """
    # ── Header fields ─────────────────────────────────────────────────────────
    vch_number  = str(rec.get("FNCNUM") or rec.get("TRANSCPTNTH") or "").strip()
    # REFERENCE: only push FNCREF if it has a value — empty string if not present (per business rule)
    reference   = str(rec.get("FNCREF") or "").strip()
    details     = str(rec.get("DETAILS") or rec.get("Details", "")).strip()
    cost_centre = str(rec.get("BRANCHNAME") or "").strip()

    # DATE: use BALDATE (value date) from Priority; fall back to TRANSDATE only — never today's date
    raw_date = rec.get("BALDATE") or rec.get("TRANSDATE") or ""
    tally_dt = _tally_date(str(raw_date)[:10]) if raw_date else ""

    narration = " | ".join(filter(None, [reference, details, vch_number]))

    # ── Build legs from FNCITEMS subform ─────────────────────────────────────
    # Each leg: (ledger_name, is_debit, amount_abs, line_cost_centre)
    legs = []

    lines = rec.get(JRNL_SUBFORM, [])
    if lines:
        for line in lines:
            # ACCDES is the account description = ledger name in Tally
            acc = str(line.get("ACCDES") or line.get("ACCNAME") or "").strip()
            if not acc:
                continue
            # DEBIT1 / CREDIT1 are the correct Priority subform amount fields
            debit  = float(line.get("DEBIT1")  or line.get("DEBIT")  or 0)
            credit = float(line.get("CREDIT1") or line.get("CREDIT") or 0)
            line_cc = str(line.get("BRANCHNAME") or cost_centre or "").strip()
            if debit > 0:
                legs.append((acc, True,  debit,  line_cc))
            elif credit > 0:
                legs.append((acc, False, credit, line_cc))
    else:
        # Header-level 2-leg fallback (no FNCITEMS subform data)
        dr_acc = str(rec.get("DEBITACC")  or rec.get("Debit Account",  "")).strip()
        cr_acc = str(rec.get("CREDITACC") or rec.get("Credit Account", "")).strip()
        amount = abs(float(rec.get("QPRICE") or rec.get("Amount") or 0))
        if dr_acc:
            legs.append((dr_acc, True,  amount, cost_centre))
        if cr_acc:
            legs.append((cr_acc, False, amount, cost_centre))

    if not legs:
        return ""  # push runner will skip this record

    # ── Render ALLLEDGERENTRIES.LIST blocks ──────────────────────────────────
    ledger_blocks = ""
    for ledger, is_debit, amt, leg_cc in legs:
        deemed  = "Yes" if is_debit else "No"
        xml_amt = f"-{amt:.2f}" if is_debit else f"{amt:.2f}"

        # CATEGORYALLOCATIONS block — wraps cost centre per leg, matching Tally's required structure
        if leg_cc:
            cat_block = f"""
          <CATEGORYALLOCATIONS.LIST>
            <CATEGORY>Primary Cost Category</CATEGORY>
            <ISDEEMEDPOSITIVE>{deemed}</ISDEEMEDPOSITIVE>
            <COSTCENTREALLOCATIONS.LIST>
              <NAME>{_xml_text(leg_cc)}</NAME>
              <AMOUNT>{xml_amt}</AMOUNT>
            </COSTCENTREALLOCATIONS.LIST>
          </CATEGORYALLOCATIONS.LIST>"""
        else:
            cat_block = ""

        ledger_blocks += f"""
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>{_xml_text(ledger)}</LEDGERNAME>
          <ISDEEMEDPOSITIVE>{deemed}</ISDEEMEDPOSITIVE>
          <AMOUNT>{xml_amt}</AMOUNT>{cat_block}
          <BANKALLOCATIONS.LIST></BANKALLOCATIONS.LIST>
          <BILLALLOCATIONS.LIST></BILLALLOCATIONS.LIST>
        </ALLLEDGERENTRIES.LIST>"""

    # Voucher-level cost centre + ISCOSTCENTRE flag (required by Tally when cost centres are used)
    vch_cc_tag = (
        f"\n            <COSTCENTRENAME>{_xml_text(cost_centre)}</COSTCENTRENAME>"
        f"\n            <ISCOSTCENTRE>Yes</ISCOSTCENTRE>"
        if cost_centre else ""
    )

    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="{JRNL_TALLY_VCH_TYPE}" ACTION="Create">
            {("<DATE>" + tally_dt + "</DATE>") if tally_dt else ""}
            {("<REFERENCEDATE>" + tally_dt + "</REFERENCEDATE>") if tally_dt else ""}
            <VOUCHERTYPENAME>{JRNL_TALLY_VCH_TYPE}</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{_xml_text(vch_number)}</VOUCHERNUMBER>
            {("<REFERENCE>" + _xml_text(reference) + "</REFERENCE>") if reference else ""}
            <NARRATION>{_xml_text(narration)}</NARRATION>
            <ISINVOICE>No</ISINVOICE>{vch_cc_tag}{ledger_blocks}
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


def run_jrnl_push(records: list, dry_run: bool, source: str) -> list:
    """Push Posted journal entries to Tally as Journal Vouchers."""
    results = []
    prog = st.progress(0)
    status_ph = st.empty()
    total = len(records)
    for i, rec in enumerate(records):
        entry_no  = str(rec.get("FNCNUM") or rec.get("TRANSCPTNTH") or rec.get("Entry No.", "?")).strip()
        reference = str(rec.get("FNCREF") or "").strip()  # only FNCREF, no fallbacks
        amount    = abs(float(rec.get("QPRICE") or rec.get("Amount") or 0))
        status_ph.markdown(f"**[{source}]** Pushing `{entry_no}` ({i+1}/{total})…")
        xml = build_jrnl_xml(rec)
        if not xml:
            results.append({
                "Entry No.": entry_no, "Reference": reference,
                "Amount": fmt_inr(amount), "Tally Type": JRNL_TALLY_VCH_TYPE,
                "Result": "⚠️ Skipped — no ledger legs found (no debit/credit accounts)",
                "XML": "", "Timestamp": datetime.now().strftime("%H:%M:%S"),
            })
        elif dry_run:
            results.append({
                "Entry No.": entry_no, "Reference": reference,
                "Amount": fmt_inr(amount), "Tally Type": JRNL_TALLY_VCH_TYPE,
                "Result": "🧪 Dry run — XML built, not pushed",
                "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S"),
            })
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({
                "Entry No.": entry_no, "Reference": reference,
                "Amount": fmt_inr(amount), "Tally Type": JRNL_TALLY_VCH_TYPE,
                "Result": f"{'✅' if ok else '❌'} {msg}",
                "XML": xml, "Tally Response": tally_raw,
                "Timestamp": datetime.now().strftime("%H:%M:%S"),
            })
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty()
    status_ph.empty()
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 4: VENDOR INVOICES  (INVOICES — Final status → Tally Purchase Invoice)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── VENDOR INVOICE CONFIG ────────────────────────────────────────────────────
VINV_FORM        = "YINVOICES"
VINV_SUBFORM     = "YINVOICEITEMS_SUBFORM"
VINV_PUSH_STATUS = "Final"

VINV_HEADER_MAP = {
    "SUPNAME":   "Vendor No.",
    "CDES":      "Vendor Name",
    "IVDATE":    "Date",
    "CURDATE":   "Date",
    "IVNUM":     "Invoice No.",
    "ORDNAME":   "Order Number",
    "QPRICE":    "Total Before Discount",
    "DISCOUNT":  "Overall Discount",
    "DISPRICE":  "Price After Discount",
    "VAT":       "VAT",
    "TOTPRICE":  "Amount Owing",
    "STATDES":   "Status",
    "WARHSNAME": "Warehouse",
    "TAXCODE":   "VAT Code",
    "PARTYVAT":  "Vendor GSTIN",
    "CODE":      "Currency",
}

VINV_LINE_MAP = {
    "PARTNAME":  "Part Number",
    "PDES":      "Part Description",
    "TQUANT":    "Quantity",
    "TUNITNAME": "Unit",
    "PRICE":     "Unit Price",
    "PERCENT":   "Discount %",
    "QPRICE":    "Total Price",
    "WARHSNAME": "Warehouse",
}

VINV_PUSH_STATUSES = {"Final"}
# ═══════════════════════════════════════════════════════════════════════════════
# GOODS RECEIVING VOUCHERS  (DOCUMENTS_P — Final status → Tally Receipt Note)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── GRV CONFIG ───────────────────────────────────────────────────────────────
GRV_FORM         = "DOCUMENTS_P"
GRV_SUBFORM      = "TRANSORDER_P_SUBFORM"  # Primary subform nav property name (matches live API)
# Fallback subform key names Priority may return for DOCUMENTS_P line items.
# The OData navigation property for DOCUMENTS_P sub-lines varies by Priority version.
# All keys are checked in order; the first non-empty list wins.
GRV_SUBFORM_ALIASES = [
    "TRANSORDER_P_SUBFORM",    # confirmed live API key (DOCUMENTS_P?$expand=TRANSORDER_P_SUBFORM)
    "TRANSORDER_P",            # standard (without _SUBFORM suffix)
    "TRANSORDERITEMS_SUBFORM", # some versions
    "TRANSORDER_SUBFORM",      # alternate
    "DRAFTORDER_SUBFORM",      # draft orders subform
    "ORDERITEMS_SUBFORM",      # generic items subform
]
GRV_PUSH_STATUS  = "Final"
GRV_RESOLVED_SUBFORM = GRV_SUBFORM  # updated at runtime by fetch_grv()

GRV_HEADER_MAP = {
    # Document identity — Priority may use DOCNO or DNAME for the GRV number
    "DOCNO":     "GRV No.",
    "DNAME":     "GRV No.",        # alternate field used in some Priority versions
    "DOCNUM":    "GRV No.",        # numeric variant
    # Vendor fields
    "SUPNAME":   "Vendor No.",
    "CDES":      "Vendor Name",
    # Date
    "CURDATE":   "Date",
    "DOCDATE":   "Date",           # some versions use DOCDATE
    # Order reference
    "ORDNAME":   "PO Reference",
    # Amounts
    "QPRICE":    "Total Before Discount",
    "VAT":       "VAT",
    "TOTPRICE":  "Total Amount",
    # Status and logistics
    "STATDES":   "Status",
    "WARHSNAME": "Warehouse",
    "TAXCODE":   "VAT Code",
    "PARTYVAT":  "Vendor GSTIN",
    "CODE":      "Currency",
    "DOCDES":    "Document Description",
    "BOOKNUM":   "Vendor Doc No.",     # Priority vendor document number → Tally Receipt Doc No.
    "IVNUM":     "Vendor Doc No.",     # alternate: vendor invoice no. field on DOCUMENTS_P
    "EXTDOCNO":  "Vendor Doc No.",     # alternate: external document number
    "SUPPREF":   "Vendor Doc No.",     # alternate: supplier reference
}

GRV_LINE_MAP = {
    "PARTNAME":    "Part Number",
    "ICODE":       "Part Number",      # alternate item code in TRANSORDER_P_SUBFORM
    "PDES":        "Part Description",
    "TDES":        "Part Description",  # alternate description in TRANSORDER_P_SUBFORM
    "TQUANT":      "Quantity",
    "RQUANT":      "Quantity",          # received quantity variant
    "TUNITNAME":   "Unit",
    "UNITNAME":    "Unit",              # alternate unit field
    "PRICE":       "Unit Price",
    "TPRICE":      "Unit Price",        # alternate price field
    "PERCENT":     "Discount %",
    "QPRICE":      "Total Price",
    "WARHSNAME":   "Warehouse",
    "TOWARHSNAME": "Warehouse",      # destination warehouse on GRV subform lines (Priority TRANSORDER_P_SUBFORM)
    "ORDNAME":     "PO Reference",
    "EPARTNAME":   "External Part No.",
    "DUEDATE":     "Due Date",          # line-level due date (used for ORDERDUEDATE in Tally)
    "REQDATE":     "Due Date",          # alternate due date field in TRANSORDER_P_SUBFORM
    "MAHI_TAXRATE": "VAT Group",        # GST % per line — now available directly on GRV subform
}

GRV_PUSH_STATUSES = {"Final"}



@st.cache_data(ttl=300, show_spinner=False)
def fetch_vendor_invoices():
    hdrs = _auth_headers()
    url  = f"{PRIORITY_BASE}/{VINV_FORM}?$expand={VINV_SUBFORM}&$top=500"
    try:
        records   = _paginate(url, hdrs)
        has_lines = any(
            isinstance(r.get(VINV_SUBFORM), list) and len(r[VINV_SUBFORM]) > 0
            for r in records
        )
        return records, has_lines
    except Exception:
        try:
            fb = _paginate(f"{PRIORITY_BASE}/{VINV_FORM}?$top=500", hdrs)
            return fb, False
        except Exception:
            return [], False

def build_vinv_header_df(raw):
    df = pd.DataFrame(raw)
    if VINV_SUBFORM in df.columns:
        df = df.drop(columns=[VINV_SUBFORM])
    if "IVDATE" in df.columns and "CURDATE" in df.columns:
        df["IVDATE"] = df["IVDATE"].fillna(df["CURDATE"])
        df = df.drop(columns=["CURDATE"])
    df = df.rename(columns={k: v for k, v in VINV_HEADER_MAP.items() if k in df.columns})
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Total Before Discount", "Overall Discount", "Price After Discount", "VAT", "Amount Owing")
    return df

def build_vinv_lines_df(raw):
    rows = []
    for inv in raw:
        lines = inv.get(VINV_SUBFORM, [])
        if not lines:
            continue
        base = {
            "Invoice No.": inv.get("IVNUM"),
            "Vendor Name": inv.get("CDES"),
            "Date":        inv.get("IVDATE") or inv.get("CURDATE"),
            "Status":      inv.get("STATDES", ""),
            "Warehouse":   inv.get("WARHSNAME", ""),
        }
        for line in lines:
            row = {**base, **{v: line.get(k) for k, v in VINV_LINE_MAP.items()}}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Quantity", "Unit Price", "Discount %", "Total Price")
    return df

def build_vinv_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy()
        df["Line Count"] = 0; df["Parts"] = ""; df["Lines Total"] = 0.0
        return df
    agg = (
        lines_df.groupby("Invoice No.")
        .agg(
            LC=("Part Description", "count"),
            LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
            LT=("Total Price", "sum"),
        )
        .reset_index()
        .rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"})
    )
    merged = header_df.merge(agg, on="Invoice No.", how="left")
    merged["Line Count"]  = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"]       = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged

# ─── GRV FETCH & BUILD ────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_grv():
    """
    Fetch DOCUMENTS_P records with line items expanded.

    Priority's OData navigation property for the DOCUMENTS_P sub-lines can be
    named differently across versions (TRANSORDER_P, TRANSORDERITEMS_SUBFORM…).
    We try each alias in sequence, expanding it in the URL. Once we get records
    that actually contain line data we stop and return those records.

    The resolved subform key is stored in GRV_RESOLVED_SUBFORM (module-level)
    so build_grv_xml and build_grv_lines_df use the same key.
    """
    global GRV_RESOLVED_SUBFORM
    hdrs = _auth_headers()

    # Try each alias — use the first one that returns line data
    for alias in GRV_SUBFORM_ALIASES:
        url = f"{PRIORITY_BASE}/{GRV_FORM}?$expand={alias}&$top=500"
        try:
            records = _paginate(url, hdrs)
            if not records:
                continue
            has_lines = any(
                isinstance(r.get(alias), list) and len(r.get(alias, [])) > 0
                for r in records
            )
            if has_lines:
                GRV_RESOLVED_SUBFORM = alias
                return records, True
            # Records returned but no lines — still store as candidate
            # (might be all header-only docs); keep trying for a better alias
            GRV_RESOLVED_SUBFORM = alias
            _candidate = (records, False)
        except Exception:
            continue

    # All aliases exhausted with no line data — return last successful fetch
    try:
        return _candidate
    except NameError:
        pass

    # Final fallback: header-only
    try:
        fb = _paginate(f"{PRIORITY_BASE}/{GRV_FORM}?$top=500", hdrs)
        GRV_RESOLVED_SUBFORM = GRV_SUBFORM
        return fb, False
    except Exception:
        GRV_RESOLVED_SUBFORM = GRV_SUBFORM
        return [], False

def build_grv_header_df(raw):
    df = pd.DataFrame(raw)
    if GRV_SUBFORM in df.columns:
        df = df.drop(columns=[GRV_SUBFORM])
    df = df.rename(columns={k: v for k, v in GRV_HEADER_MAP.items() if k in df.columns})
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Total Before Discount", "VAT", "Total Amount")
    return df

def build_grv_lines_df(raw):
    rows = []
    for rec in raw:
        # Try all known subform aliases — use whichever has data
        lines = []
        for alias in GRV_SUBFORM_ALIASES:
            candidate = rec.get(alias, [])
            if isinstance(candidate, list) and candidate:
                lines = candidate
                break
        if not lines:
            continue
        base = {
            "GRV No.":      rec.get("DOCNO") or rec.get("DNAME") or rec.get("DOCNUM"),
            "Vendor Name":  rec.get("CDES"),
            "Date":         rec.get("CURDATE") or rec.get("DOCDATE"),
            "Status":       rec.get("STATDES", ""),
            "Warehouse":    rec.get("WARHSNAME", ""),
            "PO Reference": rec.get("ORDNAME", ""),
        }
        for line in lines:
            row = {**base}
            for k, v in GRV_LINE_MAP.items():
                val = line.get(k)
                if val is not None and v not in row:
                    row[v] = val
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Quantity", "Unit Price", "Total Price")
    return df

def build_grv_merged_df(header_df, lines_df):
    if header_df.empty:
        return pd.DataFrame()
    if lines_df.empty or "GRV No." not in lines_df.columns:
        header_df = header_df.copy()
        header_df["Line Count"] = 0
        header_df["Parts"] = ""
        return header_df
    summary = (
        lines_df.groupby("GRV No.")
        .agg(
            Line_Count=("Part Number", "count"),
            Parts=("Part Number", lambda x: ", ".join(x.dropna().astype(str).unique()[:3])),
        )
        .reset_index()
        .rename(columns={"Line_Count": "Line Count"})
    )
    merged = header_df.merge(summary, on="GRV No.", how="left")
    merged["Line Count"] = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"] = merged["Parts"].fillna("")
    return merged

def _build_po_gst_lookup(po_ref: str) -> dict:
    """
    Follow the reference chain:
        GRV / MGRV  →  Order Number (ORDNAME)  →  PORDERS  →  PORDERITEMS_SUBFORM
        →  MAHI_TAXRATE per PARTNAME

    Returns a dict keyed by PARTNAME (both original-case and UPPER) → {
        'taxrate': float,    # total GST % (e.g. 18.0); 0.0 = explicitly exempt
        'taxcode': str,      # 'GST_IN' or 'GST_OT' (intra/inter-state)
        'cstm_gst': float,   # rupee GST amount from PO line (for back-calc only)
    }

    Strategy:
      Attempt 1 — $expand with $select (forces Priority OData to return MAHI_TAXRATE
                  and CSTM_GST; some versions omit custom fields without explicit $select).
      Attempt 2 — $expand without $select (fallback if server rejects nested $select).
      Attempt 3 — fetch PO header only, then fetch subform separately via navigation URL
                  (handles servers that don't support $expand at all).

    All PARTNAME keys are stored both in original case and UPPERCASE so callers can
    do lookup.get(pn.upper()) and lookup.get(pn) interchangeably.
    """
    if not po_ref or not str(po_ref).strip():
        return {}
    po_ref = str(po_ref).strip()
    hdrs   = _auth_headers()
    po_lines      = []
    header_taxcode = ""

    # ── Attempt 1: $expand with $select ──────────────────────────────────────
    try:
        url1 = (f"{PRIORITY_BASE}/PORDERS"
                f"?$expand={SUBFORM_NAV}($select=PARTNAME,QPRICE,MAHI_TAXRATE,CSTM_GST)"
                f"&$filter=ORDNAME eq '{po_ref}'&$top=1")
        recs = _paginate(url1, hdrs)
        if recs:
            header_taxcode = str(recs[0].get("TAXCODE") or "").strip()
            po_lines = recs[0].get(SUBFORM_NAV, [])
    except Exception:
        pass

    # ── Attempt 2: $expand without $select ───────────────────────────────────
    if not po_lines:
        try:
            url2 = (f"{PRIORITY_BASE}/PORDERS"
                    f"?$expand={SUBFORM_NAV}"
                    f"&$filter=ORDNAME eq '{po_ref}'&$top=1")
            recs = _paginate(url2, hdrs)
            if recs:
                header_taxcode = str(recs[0].get("TAXCODE") or "").strip()
                po_lines = recs[0].get(SUBFORM_NAV, [])
        except Exception:
            pass

    # ── Attempt 3: header only, then navigation URL for subform ──────────────
    if not po_lines:
        try:
            url3 = f"{PRIORITY_BASE}/PORDERS?$filter=ORDNAME eq '{po_ref}'&$top=1"
            recs = _paginate(url3, hdrs)
            if recs:
                header_taxcode = str(recs[0].get("TAXCODE") or "").strip()
                # Try fetching subform via navigation URL using the PO's key field
                po_key = str(recs[0].get("PORDER") or recs[0].get("KLINE") or "").strip()
                if po_key:
                    url3b = f"{PRIORITY_BASE}/PORDERS({po_key})/{SUBFORM_NAV}"
                    try:
                        po_lines = _paginate(url3b, hdrs)
                    except Exception:
                        pass
        except Exception:
            pass

    if not po_lines:
        return {}

    # ── Build lookup from PO lines ────────────────────────────────────────────
    lookup: dict = {}
    for line in po_lines:
        partname = str(line.get("PARTNAME") or "").strip()
        if not partname:
            continue

        # Read MAHI_TAXRATE directly
        try:
            taxrate = float(line.get("MAHI_TAXRATE") or 0)
        except Exception:
            taxrate = 0.0

        try:
            cstm_gst = float(line.get("CSTM_GST") or 0)
        except Exception:
            cstm_gst = 0.0

        # Back-calculate from CSTM_GST / QPRICE when MAHI_TAXRATE is absent or 0
        if taxrate == 0.0 and cstm_gst > 0:
            try:
                qprice = float(line.get("QPRICE") or 0)
                if qprice > 0:
                    raw_rate = cstm_gst / qprice * 100
                    taxrate  = float(min([5, 12, 18, 28], key=lambda s: abs(s - raw_rate)))
            except Exception:
                pass

        entry = {
            "taxrate":  taxrate,     # 0.0 is valid — means explicitly exempt
            "taxcode":  header_taxcode,
            "cstm_gst": cstm_gst,
        }
        # Store under both original case and UPPERCASE for flexible lookups
        lookup[partname]         = entry
        lookup[partname.upper()] = entry

    return lookup


@st.cache_data(ttl=300, show_spinner=False)
def _build_partname_taxrate_map() -> dict:
    """
    Build a global PARTNAME → GST% lookup by scanning ALL Purchase Orders and GRVs.

    This is the authoritative tax rate source for MGRV lines, because:
      - PINVOICEITEMS_SUBFORM never carries MAHI_TAXRATE or CSTM_GST
      - MGRV's ORDNAME may be blank or a consolidated reference, not a real PO number
      - The same item (e.g. RM-CurryLeaf) always has the same GST slab regardless
        of which PO or GRV it came through

    Strategy:
      Source 1 — PORDERS lines: read MAHI_TAXRATE directly.
      Source 2 — GRV lines: back-calculate from CSTM_GST / QPRICE.
      Source 1 takes priority; Source 2 fills gaps.

    Returns: dict keyed by PARTNAME (uppercase) → float GST% (e.g. 18.0)
    """
    rate_map: dict[str, float] = {}
    hdrs = _auth_headers()

    # ── Source 1: ALL Purchase Orders ─────────────────────────────────────────
    try:
        # $select forces Priority to return MAHI_TAXRATE and CSTM_GST
        po_url = (f"{PRIORITY_BASE}/PORDERS"
                  f"?$expand={SUBFORM_NAV}($select=PARTNAME,QPRICE,MAHI_TAXRATE,CSTM_GST)"
                  f"&$top=500")
        po_records = _paginate(po_url, hdrs)
        for po_rec in po_records:
            for line in po_rec.get(SUBFORM_NAV, []):
                pn = str(line.get("PARTNAME") or "").strip().upper()
                if not pn:
                    continue
                try:
                    taxrate = float(line.get("MAHI_TAXRATE") or 0)
                except Exception:
                    taxrate = 0.0
                # Back-calculate from CSTM_GST if MAHI_TAXRATE absent
                if taxrate == 0.0:
                    try:
                        cstm_gst = float(line.get("CSTM_GST") or 0)
                        qprice   = float(line.get("QPRICE") or 0)
                        if cstm_gst > 0 and qprice > 0:
                            raw_rate = cstm_gst / qprice * 100
                            taxrate = float(min([5, 12, 18, 28], key=lambda s: abs(s - raw_rate)))
                    except Exception:
                        pass
                # Store ALL items explicitly — including 0% exempt ones.
                # If MAHI_TAXRATE is present (even as 0), store it so MGRV Tier 1
                # lookup returns 0 for exempt items and skips GST rather than
                # falling through to the proportional-header-VAT fallback (which
                # would wrongly assign GST to a 0% item like RM-CurryLeaf).
                if line.get("MAHI_TAXRATE") is not None:
                    rate_map[pn] = taxrate  # may be 0.0 — that's intentional
                elif taxrate > 0:
                    # Rate back-calculated from CSTM_GST — only store if positive
                    rate_map[pn] = taxrate
    except Exception:
        pass

    # ── Source 2: ALL GRVs — fill gaps not found in PO ────────────────────────
    try:
        grv_url = f"{PRIORITY_BASE}/{GRV_FORM}?$expand={GRV_SUBFORM}&$top=500"
        grv_records = _paginate(grv_url, hdrs)
        for grv_rec in grv_records:
            lines = []
            for alias in GRV_SUBFORM_ALIASES:
                c = grv_rec.get(alias, [])
                if isinstance(c, list) and c:
                    lines = c
                    break
            for line in lines:
                pn = str(line.get("PARTNAME") or line.get("ICODE") or "").strip().upper()
                if not pn or pn in rate_map:
                    continue  # already have it from PO
                try:
                    cstm_gst = float(line.get("CSTM_GST") or 0)
                    qprice   = float(line.get("QPRICE") or 0)
                    if cstm_gst > 0 and qprice > 0:
                        raw_rate = cstm_gst / qprice * 100
                        taxrate = float(min([5, 12, 18, 28], key=lambda s: abs(s - raw_rate)))
                        if taxrate > 0:
                            rate_map[pn] = taxrate
                except Exception:
                    pass
    except Exception:
        pass

    return rate_map


def build_grv_xml(rec: dict) -> str:
    """
    Build a Tally Receipt Note XML (VCHTYPE=Receipt Note, ISINVOICE=No)
    from a Priority DOCUMENTS_P (GRV) record.

    Receipt Note sign convention (goods IN from vendor):
      ALLINVENTORYENTRIES  ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (stock debit)
      ACCOUNTINGALLOCATIONS (Purchase Account)   ISDEEMEDPOSITIVE=Yes, AMOUNT negative
      Party LEDGERENTRIES  ISDEEMEDPOSITIVE=No,  AMOUNT positive  (vendor — we owe)
      CGST/SGST/IGST (ITC) ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (input credit)

    Tally Purchase Routing Linkage:  PO → Receipt Note (GRV) → Purchase Invoice
    ─────────────────────────────────────────────────────────────────────────────
    | Tally Field          | XML Tag                          | Priority Source  |
    |──────────────────────|──────────────────────────────────|──────────────────|
    | Voucher Number       | VOUCHERNUMBER                    | DOCNO (GRV no.)  |
    | Reference No         | REFERENCE                        | DOCNO (GRV no.)  |
    | Receipt Doc No       | INVOICEORDERLIST > BASICORDERREF / BASICSHIPDOCUMENTREF / BASICGOODSRECEIPTNO | BOOKNUM |
    | Party A/c Name       | PARTYLEDGERNAME / PARTYNAME      | CDES             |
    | Order No(s)          | BATCHALLOCATIONS > ORDERNO       | ORDNAME (PO no.) |
    | PO Header Link       | INVOICEORDERLIST > BASICPURCHASEORDERNO | ORDNAME   |

    The ORDERNO inside BATCHALLOCATIONS.LIST is the CRITICAL field.
    Without it: PO popup will not work, GRV will not link to PO,
    pending quantity tracking will fail.
    """
    grv_no      = rec.get("DOCNO") or rec.get("GRV No.") or rec.get("DNAME") or rec.get("DOCNUM", "")
    raw_date    = rec.get("Date")      or rec.get("CURDATE", "")
    vendor      = rec.get("Vendor Name") or rec.get("CDES", "")
    warehouse   = rec.get("TOWARHSNAME") or rec.get("Warehouse") or rec.get("WARHSNAME") or "Main Location"
    branch      = str(
        rec.get("BRANCHNAME") or rec.get("Branch") or
        rec.get("BRANCH")     or rec.get("BRANCHDES") or ""
    ).strip()
    amt_total   = float(rec.get("Total Amount") or rec.get("TOTPRICE") or 0)
    gst_total   = float(rec.get("VAT") or 0)
    party_gstin = str(rec.get("Vendor GSTIN") or rec.get("PARTYVAT") or "").strip()
    po_ref      = str(rec.get("PO Reference") or rec.get("ORDNAME") or "").strip()
    # Vendor's document number → Tally Receipt Doc No.
    # Priority uses different field names across versions for this value on DOCUMENTS_P:
    #   BOOKNUM  — standard GRV vendor doc field
    #   IVNUM    — same field as vendor invoice number (used in some Priority builds)
    #   EXTDOCNO — external document number variant
    #   SUPPREF  — supplier reference number
    booknum = str(
        rec.get("BOOKNUM") or
        rec.get("Vendor Doc No.") or
        rec.get("IVNUM") or
        rec.get("EXTDOCNO") or
        rec.get("SUPPREF") or
        ""
    ).strip()
    t_date      = _tally_date(str(raw_date))

    is_intrastate = _detect_intrastate(rec)

    # Resolve line items — try the runtime-detected subform key first, then all aliases
    raw_lines = []
    for _sf_key in ([GRV_RESOLVED_SUBFORM] + GRV_SUBFORM_ALIASES):
        _candidate_lines = rec.get(_sf_key)
        if isinstance(_candidate_lines, list) and _candidate_lines:
            raw_lines = _candidate_lines
            break
    total_line_amt = sum(float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines) or 1.0

    # ── Follow References → Order Number → PO form → MAHI_TAXRATE ───────────
    #
    # GRV References tab: "Order Number" field = ORDNAME = e.g. PO26000045
    # This is the authoritative link from GRV to PO.  We follow it here:
    #   1. _build_po_gst_lookup(po_ref) fetches that exact PO (3-attempt, bulletproof)
    #   2. _build_partname_taxrate_map() scans ALL POs as a global safety net
    # Per-line ORDNAME is also checked inside the line loop below (each GRV line
    # carries its own ORDNAME — same value as References → Order Number for single-PO
    # GRVs, potentially different for multi-PO GRVs).

    # Global safety net: all POs scanned (cached 5 min)
    global_rate_map = _build_partname_taxrate_map()

    # Primary: follow header ORDNAME → fetch that PO → PARTNAME → MAHI_TAXRATE
    po_gst_lookup = _build_po_gst_lookup(po_ref)

    # Refine intra/inter-state from PO TAXCODE (GST_IN = intra, GST_OT/IGST = inter)
    if po_gst_lookup:
        _sample_taxcode = next(
            (v.get("taxcode", "") for v in po_gst_lookup.values() if isinstance(v, dict)), ""
        )
        if _sample_taxcode:
            if "GST_OT" in _sample_taxcode.upper() or "IGST" in _sample_taxcode.upper():
                is_intrastate = False
            elif "GST_IN" in _sample_taxcode.upper():
                is_intrastate = True

    inv_entries = ""
    for line in raw_lines:
        pn   = str(line.get("PARTNAME") or line.get("ICODE") or line.get("Part Number", "")).strip()
        pd_  = str(line.get("PDES")     or line.get("TDES")  or line.get("Part Description", "")).strip()
        name = resolve_po_item_name(pn, pd_)
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT") or line.get("RQUANT") or line.get("Quantity",   0))
            rate = float(line.get("PRICE")  or line.get("TPRICE")  or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE") or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        raw_unit = str(line.get("TUNITNAME") or line.get("UNITNAME") or line.get("Unit", "")).strip()
        unit = raw_unit if raw_unit else _resolve_unit(name)

        # TOWARHSNAME is the destination warehouse field on TRANSORDER_P_SUBFORM lines.
        # WARHSNAME may also appear; TOWARHSNAME takes priority as it is the GRV target location.
        line_wh_raw = str(
            line.get("TOWARHSNAME") or
            line.get("WARHSNAME")   or
            line.get("Warehouse")   or
            warehouse or ""
        ).strip() or "Main Location"
        line_wh = _map_priority_godown(line_wh_raw)

        # PO reference per line — prefer line-level ORDNAME, fall back to header-level po_ref.
        # This is the CRITICAL field that enables Tally's "List of Orders" popup and
        # links the Receipt Note ↔ Purchase Order for pending quantity tracking.
        line_po = str(line.get("ORDNAME") or po_ref or "").strip()

        # Due date per line — used for ORDERDUEDATE in BATCHALLOCATIONS.LIST
        # Priority sends this in DUEDATE or REQDATE on the sub-form line.
        # Falls back to the GRV header date so the field is never blank in Tally.
        due_raw = line.get("DUEDATE") or line.get("REQDATE") or line.get("Due Date") or raw_date
        try:
            due_date = (pd.to_datetime(str(due_raw)).strftime("%d-%b-%y")
                        if due_raw else datetime.today().strftime("%d-%b-%y"))
        except Exception:
            due_date = datetime.today().strftime("%d-%b-%y")

        # ── GST% resolution ───────────────────────────────────────────────────────
        #
        # VAT Group column is now present directly on the GRV subform (MAHI_TAXRATE),
        # so we no longer need to follow the PO reference chain as the primary source.
        #
        # Tier 1 (fastest): MAHI_TAXRATE on the GRV line itself — read directly.
        #         Priority now populates this via the VAT Group column on the GRV subform.
        # Tier 2: per-line ORDNAME -> fetch that exact PO -> match PARTNAME.
        #         Fallback for lines where MAHI_TAXRATE is absent/zero on the GRV.
        # Tier 3: global_rate_map — all POs scanned; sentinel honours 0% exempt items.
        # Tier 4: proportional share of header VAT — absolute last resort only.
        _MISSING = object()
        total_gst_pct = 0.0
        _found        = False

        # Tier 1 — read MAHI_TAXRATE directly from GRV line (VAT Group column)
        _raw_grv_rate = line.get("MAHI_TAXRATE")
        if _raw_grv_rate is not None:
            try:
                total_gst_pct = float(_raw_grv_rate)
                _found = True
            except Exception:
                pass

        # Tier 2 — follow line ORDNAME -> PO form -> MAHI_TAXRATE for this PARTNAME
        #          (used only when GRV line has no MAHI_TAXRATE)
        if not _found:
            line_ordname = str(line.get("ORDNAME") or po_ref or "").strip()
            if line_ordname:
                if line_ordname == po_ref:
                    _po_lk = po_gst_lookup
                else:
                    _po_lk = _build_po_gst_lookup(line_ordname)
                for _key in (pn.upper(), pn, name.upper(), name):
                    _entry = _po_lk.get(_key)
                    if _entry is not None:
                        total_gst_pct = float(_entry.get("taxrate", 0.0)) if isinstance(_entry, dict) else float(_entry)
                        _found = True
                        break

        # Tier 3 — global map: all POs scanned; sentinel prevents 0% fallthrough
        if not _found:
            _g = global_rate_map.get(pn.upper(), _MISSING)
            if _g is _MISSING:
                _g = global_rate_map.get(name.upper(), _MISSING)
            if _g is not _MISSING:
                total_gst_pct = float(_g)   # 0.0 = exempt — no further fallback
                _found = True

        # Tier 4 — proportional share of header VAT (last resort only)
        if not _found and gst_total > 0 and amt > 0:
            _line_vat = round(gst_total * (amt / total_line_amt), 2)
            total_gst_pct = round(_line_vat / amt * 100, 2) if _line_vat > 0 else 0.0

        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>""" if total_gst_pct > 0 else ""

        # Receipt Note: stock IN — ISDEEMEDPOSITIVE=Yes, AMOUNT negative
        #
        # BATCHALLOCATIONS tag order follows the Tally Item Allocations popup exactly:
        #   TRACKINGNUMBER  → "Tracking No"  (GRV number — links Receipt Note in tracking chain)
        #   ORDERNO         → "Order No"     (PO number  — links back to Purchase Order)
        #   ORDERDUEDATE    → "Due On"       (PO line due date)
        #   AMOUNT / QTY    follow after date fields
        _grv_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch}</NAME>
                            <AMOUNT>-{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>-{amt:.2f}</AMOUNT>
                <VATASSBLVALUE>{amt:.2f}</VATASSBLVALUE>
                <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{line_wh}</DESTINATIONGODOWNNAME>
                    <TRACKINGNUMBER>{grv_no}</TRACKINGNUMBER>
                    <ORDERNO>{line_po}</ORDERNO>
                    <ORDERDUEDATE>{due_date}</ORDERDUEDATE>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_PURCHASE}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    {_grv_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # ── Slab-wise GST ledger entries (Input Tax Credit) ──────────────────────
    # Stamp MAHI_TAXRATE onto each GRV line before passing to _build_gst_groups.
    # Now that the GRV subform carries MAHI_TAXRATE directly (VAT Group column),
    # Tier 1 reads it from the line itself — no PO API call needed for most lines.
    # Sentinel (_MISS) ensures 0% exempt items are stamped 0.0 and cleanly skipped
    # by _build_gst_groups — they never reach the proportional-VAT fallback.
    # CSTM_GST is NOT copied: GRV qty may differ from PO qty, so we let
    # _build_gst_groups recompute the rupee amount as GRV_QPRICE × MAHI_TAXRATE%.
    _MISS = object()
    enriched_lines = []
    for line in raw_lines:
        _pn  = str(line.get("PARTNAME") or line.get("ICODE") or "").strip()
        _lpo = str(line.get("ORDNAME") or po_ref or "").strip()
        enriched = dict(line)
        enriched.pop("CSTM_GST", None)   # never copy PO rupee amount — qty may differ
        _rate = None

        # Tier 1: MAHI_TAXRATE directly on GRV line (VAT Group column)
        _raw_direct = line.get("MAHI_TAXRATE")
        if _raw_direct is not None:
            try:
                _rate = _decode_mahi_taxrate(_raw_direct)
            except Exception:
                pass

        # Tier 2: per-line ORDNAME -> that PO -> MAHI_TAXRATE for this PARTNAME
        if _rate is None and _lpo:
            _lk = po_gst_lookup if _lpo == po_ref else _build_po_gst_lookup(_lpo)
            for _k in (_pn.upper(), _pn):
                _d = _lk.get(_k)
                if _d is not None:
                    _rate = float(_d.get("taxrate", 0.0)) if isinstance(_d, dict) else float(_d)
                    break

        # Tier 3: global map (sentinel — 0.0 = exempt, no fallthrough)
        if _rate is None:
            _g = global_rate_map.get(_pn.upper(), _MISS)
            if _g is not _MISS:
                _rate = float(_g)

        # Stamp rate (including 0.0 for exempt items — _build_gst_groups skips them)
        if _rate is not None:
            enriched["MAHI_TAXRATE"] = _rate
        enriched_lines.append(enriched)
    gst_groups_grv = _build_gst_groups(enriched_lines, is_intrastate, gst_field="CSTM_GST", direction="input")

    # Final fallback: if still no group data, use header VAT with a flat slab guess
    if not gst_groups_grv and gst_total > 0:
        if is_intrastate:
            gst_groups_grv = {
                _gst_ledger_name("CGST", "9", "input"): round(gst_total / 2, 2),
                _gst_ledger_name("SGST", "9", "input"): round(gst_total - round(gst_total / 2, 2), 2),
            }
        else:
            gst_groups_grv = {_gst_ledger_name("IGST", "18", "input"): gst_total}
    gst_entries = _gst_group_ledger_entries(
        gst_groups_grv, is_intrastate, isdeemedpositive="Yes", sign="-"
    )

    gstin_tag   = f"<PARTYGSTIN>{party_gstin}</PARTYGSTIN>" if party_gstin else ""
    po_order_tag = f"""
                        <INVOICEORDERLIST.LIST>
                            <BASICORDERDATE>{t_date}</BASICORDERDATE>
                            <ORDERTYPE>Purchase Order</ORDERTYPE>
                            <BASICPURCHASEORDERNO>{po_ref}</BASICPURCHASEORDERNO>
                            <BASICORDERREF>{booknum}</BASICORDERREF>
                            <BASICSHIPDOCUMENTREF>{booknum}</BASICSHIPDOCUMENTREF>
                            <BASICGOODSRECEIPTNO>{booknum}</BASICGOODSRECEIPTNO>
                            <BASICSHIPPINGDATE>{t_date}</BASICSHIPPINGDATE>
                        </INVOICEORDERLIST.LIST>""" if po_ref else ""

    # Receipt Note uses ISINVOICE=No — pure goods receipt, no financial posting
    # Party leg is positive (we owe vendor for goods received)
    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Receipt Note" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <OVRDDEFAULTS>Yes</OVRDDEFAULTS>
                        <OVRDVCHDATE>Yes</OVRDVCHDATE>
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Receipt Note</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{grv_no}</VOUCHERNUMBER>
                        <REFERENCE>{grv_no}</REFERENCE>
                        <BASICSHIPDOCUMENTNO>{booknum}</BASICSHIPDOCUMENTNO>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>Maharashtra</STATENAME>
                        <PLACEOFSUPPLY>Maharashtra</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{vendor}</PARTYLEDGERNAME>
                        <PARTYNAME>{vendor}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Goods Receiving Voucher from Priority ERP — PO: {po_ref}</NARRATION>
                        <ISINVOICE>No</ISINVOICE>
                        <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
                        <DIFFACTUALQTY>Yes</DIFFACTUALQTY>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{vendor}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amt_total:.2f}</AMOUNT>
                            <BILLALLOCATIONS.LIST>
                                <NAME>{grv_no}</NAME>
                                <BILLTYPE>New Ref</BILLTYPE>
                                <AMOUNT>{amt_total:.2f}</AMOUNT>
                            </BILLALLOCATIONS.LIST>
                        </LEDGERENTRIES.LIST>{gst_entries}
                        {po_order_tag}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()


def run_grv_push(records: list, dry_run: bool, source: str) -> list:
    """Push Final GRVs to Tally as Receipt Note vouchers."""
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(records)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing vendor ledgers & stock items in Tally…")
        for rec in records:
            v = rec.get("Vendor Name") or rec.get("CDES", "")
            if v: ensure_vendor_ledger(v, "Sundry Creditors")
            _grv_lines_for_push = []
            for _sf in ([GRV_RESOLVED_SUBFORM] + GRV_SUBFORM_ALIASES):
                _cand = rec.get(_sf)
                if isinstance(_cand, list) and _cand:
                    _grv_lines_for_push = _cand
                    break
            for line in _grv_lines_for_push:
                item_name = resolve_po_item_name(
                    line.get("PARTNAME", "") or line.get("ICODE", ""),
                    line.get("PDES", "") or line.get("TDES", ""),
                )
                if item_name:
                    _pn = str(line.get("PARTNAME") or line.get("ICODE") or "").strip()
                    _is_intra = _detect_intrastate(rec)
                    _rate = _decode_mahi_taxrate(line.get("MAHI_TAXRATE")) if line.get("MAHI_TAXRATE") is not None else 0.0
                    if _rate == 0.0:
                        _g = _build_partname_taxrate_map().get(_pn.upper())
                        if _g is not None:
                            _rate = float(_g)
                    ensure_stock_item(item_name, "", gst_rate=_rate, is_intrastate=_is_intra)
        status_ph.info("⚙ Step 2/2 — Pushing Receipt Note vouchers to Tally…")
    for i, rec in enumerate(records):
        grv_id  = rec.get("DOCNO") or rec.get("GRV No.") or rec.get("DNAME") or rec.get("DOCNUM", "?")
        status  = rec.get("Status")     or rec.get("STATDES", "")
        vendor  = rec.get("Vendor Name") or rec.get("CDES", "")
        amount  = rec.get("Total Amount") or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{grv_id}` ({i+1}/{total})…")
        xml = build_grv_xml(rec)
        if dry_run:
            results.append({"Source": source, "GRV No": grv_id, "Status": status,
                            "Vendor": vendor, "Amount": fmt_inr(amount),
                            "Tally Type": "Receipt Note", "Result": "🧪 Dry run — XML built, not pushed",
                            "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({"Source": source, "GRV No": grv_id, "Status": status,
                            "Vendor": vendor, "Amount": fmt_inr(amount),
                            "Tally Type": "Receipt Note",
                            "Result": f"{'✅' if ok else '❌'} {msg}",
                            "XML": xml, "Tally Response": tally_raw,
                            "Timestamp": datetime.now().strftime("%H:%M:%S")})
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results


def build_vinv_xml(inv: dict) -> str:
    """
    Build a Tally Purchase Invoice XML (ISINVOICE=Yes, VCHTYPE=Purchase)
    from a Priority INVOICES (vendor invoice) record.

    Sign convention (Purchase Invoice — stock IN, we owe vendor):
      ALLINVENTORYENTRIES  ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (stock debit)
      ACCOUNTINGALLOCATIONS (Purchase Account)   ISDEEMEDPOSITIVE=Yes, AMOUNT negative
      Party LEDGERENTRIES  ISDEEMEDPOSITIVE=No,  AMOUNT positive  (creditor — we owe)
      CGST/SGST/IGST (ITC) ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (input credit)

    IMPORTANT — no-line fallback:
      If Priority returns 0 line items (subform empty / not yet expanded), we fall back to a
      pure-accounting Purchase voucher (ISINVOICE=No, no ALLINVENTORYENTRIES) using only a
      Purchase Account ledger entry + party ledger.  This avoids the Tally EXCEPTIONS=1
      "voucher structure mismatch" error that occurs when a voucher has a party ledger but
      no balancing inventory or purchase ledger entry.
    """
    inv_no      = inv.get("Invoice No.") or inv.get("IVNUM", "")
    raw_date    = inv.get("Date")        or inv.get("IVDATE", "") or inv.get("CURDATE", "")
    vendor      = inv.get("Vendor Name") or inv.get("CDES", "")
    warehouse   = inv.get("Warehouse")   or inv.get("WARHSNAME", "Main Location")
    amt_owing   = float(inv.get("Amount Owing") or inv.get("TOTPRICE") or 0)
    gst_total   = float(inv.get("VAT") or 0)
    party_gstin = str(inv.get("Vendor GSTIN") or inv.get("PARTYVAT") or "").strip()
    t_date      = _tally_date(str(raw_date))

    is_intrastate = _detect_intrastate(inv)    # TAXCODE + STATENAME vs COMPANY_STATE

    # ── Resolve subform lines — try both possible key names Priority may return ──
    # VINV_SUBFORM = "YINVOICEITEMS_SUBFORM" — matches Priority OData navigation property
    raw_lines = inv.get(VINV_SUBFORM) or []

    total_line_amt = sum(float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines) or 1.0

    inv_entries = ""
    for line in raw_lines:
        pn   = str(line.get("PARTNAME") or line.get("Part Number", "")).strip()
        pd_  = str(line.get("PDES")     or line.get("Part Description", "")).strip()
        name = resolve_po_item_name(pn, pd_)
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT") or line.get("Quantity",   0))
            rate = float(line.get("PRICE")  or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE") or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        raw_unit = str(line.get("TUNITNAME") or line.get("Unit", "")).strip()
        unit = raw_unit if raw_unit else _resolve_unit(name)

        line_wh = str(line.get("WARHSNAME") or line.get("Warehouse") or warehouse or "Main Location").strip() or "Main Location"
        line_wh = _map_priority_godown(line_wh)

        # ── NEW: Read GST% from MAHI_TAXRATE directly ─────────────────────────
        raw_taxrate = line.get("MAHI_TAXRATE")
        if raw_taxrate is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(raw_taxrate)
            except Exception:
                total_gst_pct = 0.0
        else:
            _lv = round(gst_total * (amt / total_line_amt), 2) if amt > 0 and gst_total > 0 else 0.0
            total_gst_pct = round(_lv / amt * 100, 2) if amt > 0 and _lv > 0 else 0.0
        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>""" if total_gst_pct > 0 else ""

        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>-{amt:.2f}</AMOUNT>
                <VATASSBLVALUE>{amt:.2f}</VATASSBLVALUE>
                <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{line_wh}</DESTINATIONGODOWNNAME>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_PURCHASE}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # ── Slab-wise GST ledger entries — VINV (Input Tax Credit — debit side) ────
    gst_groups_vinv = _build_gst_groups(raw_lines, is_intrastate, gst_field="VAT", direction="input")
    if not gst_groups_vinv and gst_total > 0:
        if is_intrastate:
            gst_groups_vinv = {
                _gst_ledger_name("CGST", "9", "input"): round(gst_total / 2, 2),
                _gst_ledger_name("SGST", "9", "input"): round(gst_total - round(gst_total / 2, 2), 2),
            }
        else:
            gst_groups_vinv = {_gst_ledger_name("IGST", "18", "input"): gst_total}
    gst_entries = _gst_group_ledger_entries(
        gst_groups_vinv, is_intrastate, isdeemedpositive="Yes", sign="-"
    )

    gstin_tag = f"<PARTYGSTIN>{party_gstin}</PARTYGSTIN>" if party_gstin else ""

    # ── Taxable base = amt_owing minus GST ────────────────────────────────────
    taxable_base = round(amt_owing - gst_total, 2)

    # ── No-line fallback: pure accounting Purchase voucher ────────────────────
    # When Priority returns 0 inventory lines (subform not expanded or invoice is
    # service/expense-only), emit a flat Purchase voucher with:
    #   Dr  Purchase Account  (taxable_base)
    #   Dr  CGST/SGST or IGST (gst_total, if any)
    #   Cr  Vendor ledger     (amt_owing)
    # This is ISINVOICE=No — Tally accepts it without an inventory structure.
    if not inv_entries.strip():
        no_line_purchase = f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{LEDGER_PURCHASE}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{taxable_base:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
        xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Accounting Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <REFERENCE>{inv_no}</REFERENCE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>Maharashtra</STATENAME>
                        <PLACEOFSUPPLY>Maharashtra</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{vendor}</PARTYLEDGERNAME>
                        <PARTYNAME>{vendor}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Vendor Invoice from Priority ERP (no line items — accounting entry)</NARRATION>
                        <ISINVOICE>No</ISINVOICE>
                        <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{vendor}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amt_owing:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{no_line_purchase}{gst_entries}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return xml.strip()

    # ── Normal path: inventory invoice ────────────────────────────────────────
    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <REFERENCE>{inv_no}</REFERENCE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>Maharashtra</STATENAME>
                        <PLACEOFSUPPLY>Maharashtra</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{vendor}</PARTYLEDGERNAME>
                        <PARTYNAME>{vendor}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Vendor Invoice from Priority ERP</NARRATION>
                        <ISINVOICE>Yes</ISINVOICE>
                        <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{vendor}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amt_owing:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{gst_entries}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()

def run_vinv_push(invoices: list, dry_run: bool, source: str) -> list:
    """Push Final vendor invoices to Tally as Purchase Invoice vouchers (ISINVOICE=Yes)."""
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(invoices)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing vendor ledgers & stock items in Tally…")
        for rec in invoices:
            v = rec.get("Vendor Name") or rec.get("CDES", "")
            if v: ensure_vendor_ledger(v, "Sundry Creditors")
            for line in (rec.get(VINV_SUBFORM) or []):
                item_name = resolve_po_item_name(line.get("PARTNAME", ""), line.get("PDES", ""))
                if item_name:
                    _pn = str(line.get("PARTNAME") or "").strip()
                    _is_intra = _detect_intrastate(rec)
                    _rate = _decode_mahi_taxrate(line.get("MAHI_TAXRATE")) if line.get("MAHI_TAXRATE") is not None else 0.0
                    if _rate == 0.0:
                        _g = _build_partname_taxrate_map().get(_pn.upper())
                        if _g is not None:
                            _rate = float(_g)
                    ensure_stock_item(item_name, "", gst_rate=_rate, is_intrastate=_is_intra)
        status_ph.info("⚙ Step 2/2 — Pushing Purchase Invoice vouchers to Tally…")
    for i, rec in enumerate(invoices):
        inv_no  = rec.get("Invoice No.") or rec.get("IVNUM", "?")
        status  = rec.get("Status")      or rec.get("STATDES", "")
        vendor  = rec.get("Vendor Name") or rec.get("CDES", "")
        amount  = rec.get("Amount Owing") or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{inv_no}` ({i+1}/{total})…")
        xml = build_vinv_xml(rec)
        if dry_run:
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Vendor": vendor, "Amount": fmt_inr(amount),
                            "Tally Type": "Purchase (Invoice)", "Result": "🧪 Dry run — XML built, not pushed",
                            "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Vendor": vendor, "Amount": fmt_inr(amount),
                            "Tally Type": "Purchase (Invoice)",
                            "Result": f"{'✅' if ok else '❌'} {msg}",
                            "XML": xml, "Tally Response": tally_raw,
                            "Timestamp": datetime.now().strftime("%H:%M:%S")})
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE: MULTI GRV INVOICE  (PINVOICES — Final status → Tally Purchase Invoice)
# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 4: MULTI GRV INVOICE  (PINVOICES — Final status → Tally Purchase Invoice)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── MULTI GRV INVOICE CONFIG ─────────────────────────────────────────────────
MGRV_FORM        = "PINVOICES"
MGRV_SUBFORM     = "PINVOICEITEMS_SUBFORM"
MGRV_PUSH_STATUS = "Final"

MGRV_HEADER_MAP = {
    "SUPNAME":   "Vendor No.",
    "SUPDES":    "Vendor Name",   # PINVOICES uses SUPDES for vendor display name
    "CDES":      "Vendor Name",   # fallback — kept for compatibility
    "IVDATE":    "Date",
    "CURDATE":   "Date",
    "IVNUM":     "Internal No.",      # Priority internal GI number — distinct from supplier-facing BOOKNUM
    "ORDNAME":   "Order Number",
    "QPRICE":    "Total Before Discount",
    "DISCOUNT":  "Overall Discount",
    "DISPRICE":  "Price After Discount",
    "VAT":       "VAT",
    "TOTPRICE":  "Amount Owing",
    "STATDES":   "Status",
    "WARHSNAME": "Warehouse",
    "BRANCHNAME": "Branch",          # header-level branch code (e.g. R01-AN) → Tally GODOWNNAME
    "TAXCODE":   "VAT Code",
    "PARTYVAT":  "Vendor GSTIN",
    "STATENAME": "Vendor State",  # vendor's registered state for IGST/CGST detection
    "CODE":      "Currency",
    "DOCNO":     "Document Number",   # GRN/Receipt Note number (GR...) — used as Receipt Note No. in Tally
    "BOOKNUM":   "Invoice No.",       # Supplier's actual invoice number (98...) — displayed & used for duplicate detection
    "PAYDATE":   "Payment Date",      # Payment due date from Priority → ORDERDUEDATE in BATCHALLOCATIONS.LIST
}

MGRV_LINE_MAP = {
    "PARTNAME":    "Part Number",
    "PDES":        "Part Description",
    "TQUANT":      "Quantity",
    "TUNITNAME":   "Unit",
    "PRICE":       "Unit Price",
    "PERCENT":     "Discount %",
    "QPRICE":      "Total Price",
    "VAT":         "Line GST",       # per-line GST rupee amount from PINVOICEITEMS
    "WARHSNAME":   "Warehouse",
    "MAHI_TAXRATE": "VAT Group",     # GST % per line — now available directly on Multi GRV subform
    "RBS_TAXCODE":  "VAT Group Code", # New: VAT Group Code on PINVOICEITEMS subform (e.g. "012"=12%, "028"=28%, "001"=exempt)
                                     # This is now the PRIMARY tax source — eliminates PO API lookups entirely.
    "DOCNO":       "GRV No.",        # Per-line GRV/Receipt Note number from PINVOICEITEMS subform
                                     # (multi-GRV invoice: each line carries its own GRV number here;
                                     #  used as TRACKINGNUMBER so Tally links each item to the correct GRV)
}

MGRV_PUSH_STATUSES = {"Final"}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_mgrv_invoices():
    hdrs = _auth_headers()
    # $select explicitly requests PAYDATE (and all other header fields) because
    # Priority OData silently omits custom/extended fields unless asked for.
    # Without this, PAYDATE is missing from the response and due date stays blank.
    header_select = (
        "SUPNAME,SUPDES,CDES,IVDATE,CURDATE,IVNUM,ORDNAME,"
        "QPRICE,DISCOUNT,DISPRICE,VAT,TOTPRICE,STATDES,WARHSNAME,"
        "TAXCODE,PARTYVAT,STATENAME,CODE,DOCNO,BOOKNUM,PAYDATE"
    )
    # Do NOT use nested $select inside $expand for the subform.
    # CINVOICES/MSINV works with a bare $expand and RBS_TAXCODE comes back naturally —
    # the same applies here. Nested $select on PINVOICEITEMS causes Priority OData to
    # either fail or return empty lines on some server versions, triggering an extra
    # retry round-trip and doubling fetch time.
    url  = (f"{PRIORITY_BASE}/{MGRV_FORM}"
            f"?$select={header_select}"
            f"&$expand={MGRV_SUBFORM}"
            f"&$top=500")
    try:
        records   = _paginate(url, hdrs)
        has_lines = any(
            isinstance(r.get(MGRV_SUBFORM), list) and len(r[MGRV_SUBFORM]) > 0
            for r in records
        )
        return records, has_lines
    except Exception:
        # Retry without $select in case the server rejects it
        try:
            fb_url = f"{PRIORITY_BASE}/{MGRV_FORM}?$expand={MGRV_SUBFORM}&$top=500"
            fb = _paginate(fb_url, hdrs)
            return fb, False
        except Exception:
            return [], False

def build_mgrv_header_df(raw):
    df = pd.DataFrame(raw)
    if MGRV_SUBFORM in df.columns:
        df = df.drop(columns=[MGRV_SUBFORM])
    if "IVDATE" in df.columns and "CURDATE" in df.columns:
        df["IVDATE"] = df["IVDATE"].fillna(df["CURDATE"])
        df = df.drop(columns=["CURDATE"])
    df = df.rename(columns={k: v for k, v in MGRV_HEADER_MAP.items() if k in df.columns})
    df = _parse_dates(df, "Date", "Payment Date")
    df = _to_num(df, "Total Before Discount", "Overall Discount", "Price After Discount", "VAT", "Amount Owing")
    return df

def build_mgrv_lines_df(raw):
    rows = []
    for inv in raw:
        lines = inv.get(MGRV_SUBFORM, [])
        if not lines:
            continue
        base = {
            "Invoice No.": inv.get("BOOKNUM") or inv.get("IVNUM"),  # show supplier invoice no. (BOOKNUM/98...)
            "Vendor Name": inv.get("CDES"),
            "Date":        inv.get("IVDATE") or inv.get("CURDATE"),
            "Status":      inv.get("STATDES", ""),
            "Warehouse":   inv.get("WARHSNAME", ""),
        }
        for line in lines:
            row = {**base, **{v: line.get(k) for k, v in MGRV_LINE_MAP.items()}}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Quantity", "Unit Price", "Discount %", "Total Price", "Line GST")
    return df

def build_mgrv_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy()
        df["Line Count"] = 0; df["Parts"] = ""; df["Lines Total"] = 0.0
        return df
    agg = (
        lines_df.groupby("Invoice No.")
        .agg(
            LC=("Part Description", "count"),
            LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
            LT=("Total Price", "sum"),
        )
        .reset_index()
        .rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"})
    )
    merged = header_df.merge(agg, on="Invoice No.", how="left")
    merged["Line Count"]  = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"]       = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged

def build_mgrv_xml(inv: dict) -> str:
    """
    Build a Tally Purchase Invoice XML (ISINVOICE=Yes, VCHTYPE=Purchase)
    from a Priority PINVOICES (Multi GRV invoice) record.

    Sign convention (Purchase Invoice — stock IN, we owe vendor):
      ALLINVENTORYENTRIES  ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (stock debit)
      ACCOUNTINGALLOCATIONS (Purchase Account)   ISDEEMEDPOSITIVE=Yes, AMOUNT negative
      Party LEDGERENTRIES  ISDEEMEDPOSITIVE=No,  AMOUNT positive  (creditor — we owe)
      CGST/SGST/IGST (ITC) ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (input credit)

    IMPORTANT — no-line fallback:
      If Priority returns 0 line items (subform empty / not yet expanded), we fall back to a
      pure-accounting Purchase voucher (ISINVOICE=No, no ALLINVENTORYENTRIES) using only a
      Purchase Account ledger entry + party ledger.  This avoids the Tally EXCEPTIONS=1
      "voucher structure mismatch" error that occurs when a voucher has a party ledger but
      no balancing inventory or purchase ledger entry.
    """
    inv_no      = inv.get("Internal No.") or inv.get("IVNUM", "")
    booknum     = str(inv.get("Invoice No.") or inv.get("BOOKNUM") or "").strip()  # Priority BOOKNUM — supplier's actual invoice number → Tally Supplier Invoice No.
    doc_no      = str(inv.get("Document Number") or inv.get("DOCNO") or "").strip() or inv_no  # Priority DOCNO — GR... Receipt Note number → Tally Receipt Note No.
    raw_date    = inv.get("Date")        or inv.get("IVDATE", "") or inv.get("CURDATE", "")
    # PINVOICES uses SUPDES for vendor name; fall back to CDES for other forms
    vendor      = inv.get("Vendor Name") or inv.get("SUPDES", "") or inv.get("CDES", "")
    warehouse   = inv.get("Warehouse")   or inv.get("WARHSNAME", "Main Location")
    # BRANCHNAME is the main-form field on PINVOICES that holds the branch/godown
    # code (e.g. R01-AN). Use it raw — Tally godowns are named by the short code.
    header_wh   = str(inv.get("Branch") or inv.get("BRANCHNAME") or "").strip() or warehouse
    branch      = str(
        inv.get("BRANCHNAME") or inv.get("Branch") or
        inv.get("BRANCH")     or inv.get("BRANCHDES") or ""
    ).strip()
    amt_owing   = float(inv.get("Amount Owing") or inv.get("TOTPRICE") or 0)
    gst_total   = float(inv.get("VAT") or 0)
    party_gstin = str(inv.get("Vendor GSTIN") or inv.get("PARTYVAT") or "").strip()
    # Vendor state: from mapped header field or raw API field — used for IGST vs CGST/SGST
    vendor_state = str(inv.get("Vendor State") or inv.get("STATENAME") or "").strip()
    t_date      = _tally_date(str(raw_date))

    # ── Payment due date — from Priority PAYDATE field ────────────────────────
    # PAYDATE is the payment due date on the PINVOICES header (e.g. 08/06/26).
    # Used as ORDERDUEDATE inside BATCHALLOCATIONS.LIST so Tally shows the
    # correct due date on each inventory line (confirmed from live Tally XML).
    # Falls back to the invoice date itself when PAYDATE is absent.
    # IMPORTANT: must use _tally_date() → YYYYMMDD format (e.g. 20260608),
    # NOT strftime("%d-%b-%y") — Tally rejects non-YYYYMMDD dates and leaves
    # the field blank in the voucher.
    raw_pay_date = inv.get("Payment Date") or inv.get("PAYDATE") or raw_date
    # Tally ORDERDUEDATE format is DD-Mon-YY (e.g. 29-May-26) as confirmed from
    # a live Tally export XML — NOT YYYYMMDD which is only for voucher DATE fields.
    try:
        pay_date = pd.to_datetime(str(raw_pay_date)).strftime("%d-%b-%y") if raw_pay_date else ""
    except Exception:
        pay_date = ""

    is_intrastate = _detect_intrastate(inv)    # TAXCODE + STATENAME vs COMPANY_STATE

    # ── Resolve subform lines — try both possible key names Priority may return ──
    # MGRV_SUBFORM = "PINVOICEITEMS_SUBFORM" — matches Priority OData navigation property
    raw_lines = inv.get(MGRV_SUBFORM) or []

    # ── Collect all unique GRV numbers + their dates from subform lines ──────────
    # Each PINVOICEITEMS row carries its own DOCNO (the GR... number it came from)
    # and optionally a UDATE/CURDATE/DOCDATE for that GRV.
    # We gather them in order (deduped) as (grv_no, date_str) pairs so Tally can
    # render each GRV on its own line with its date in Receipt Details.
    _seen_grv = set()
    all_grv_pairs = []   # list of (grv_no, tally_date_str)
    for _l in raw_lines:
        _g = str(_l.get("DOCNO") or "").strip()
        if _g and _g not in _seen_grv:
            _seen_grv.add(_g)
            # Try to get the GRV's own date from the line; fall back to invoice date
            _raw_grv_date = (
                _l.get("UDATE") or _l.get("DOCDATE") or _l.get("CURDATE") or
                _l.get("IVDATE") or raw_date
            )
            _grv_date_str = _tally_date(str(_raw_grv_date)) if _raw_grv_date else t_date
            all_grv_pairs.append((_g, _grv_date_str))
    # Fall back to header doc_no if subform lines carry no DOCNO
    if not all_grv_pairs and doc_no:
        all_grv_pairs = [(doc_no, t_date)]
    all_grv_nos     = [p[0] for p in all_grv_pairs]
    all_grv_nos_str = ", ".join(all_grv_nos)   # e.g. "GR26000060, GR26000061"

    total_line_amt = sum(float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines) or 1.0

    # ── Fetch GST details ────────────────────────────────────────────────────────
    # NEW PRIMARY SOURCE: RBS_TAXCODE on each PINVOICEITEMS_SUBFORM line.
    # e.g. "012" → 12%, "028" → 28%, "001" → exempt (0%).
    # _decode_mahi_taxrate already handles the leading-zero encoding correctly.
    #
    # If ALL lines carry RBS_TAXCODE we skip the expensive PO API lookups entirely
    # (no _build_partname_taxrate_map / _build_po_gst_lookup calls).
    # Only fall back to the PO chain for lines where RBS_TAXCODE is absent/blank.
    _rbs_covered = all(
        str(l.get("RBS_TAXCODE") or "").strip() != ""
        for l in raw_lines
    ) if raw_lines else False

    if _rbs_covered:
        # Fast path: tax data is entirely on the subform — no PO API calls needed.
        global_rate_map = {}
        mgrv_po_ref     = str(inv.get("Order Number") or inv.get("ORDNAME") or "").strip()
        po_gst_lookup   = {}
    else:
        # Slow path: some lines are missing RBS_TAXCODE — fall back to PO chain.
        # PINVOICEITEMS lines may still lack MAHI_TAXRATE/CSTM_GST on older records.
        #   1. _build_partname_taxrate_map() — scans ALL PO + GRV lines globally.
        #   2. _build_po_gst_lookup(ORDNAME) — single-PO fetch for intra/inter-state.
        global_rate_map = _build_partname_taxrate_map()  # PARTNAME.upper() -> float %
        mgrv_po_ref     = str(inv.get("Order Number") or inv.get("ORDNAME") or "").strip()
        po_gst_lookup   = _build_po_gst_lookup(mgrv_po_ref) if mgrv_po_ref else {}

    # ── Build INVOICEDELNOTES.LIST blocks — one per GRV, each with its own date ──
    # Confirmed from live Tally export XML: the "Receipt Note No(s)" field in
    # Receipt Details is populated by INVOICEDELNOTES.LIST (not INVOICEORDERLIST).
    # Each block has BASICSHIPPINGDATE + BASICSHIPDELIVERYNOTE (the GRV number).
    # INVOICEORDERLIST.LIST is left empty (Tally renders it that way for PO linkage).
    # When a single GRV is converted to invoice, ORDNAME on the header holds the PO
    # number — populate INVOICEORDERLIST so Tally shows it in Order No(s).
    # For multi-GRV invoices ORDNAME is blank/consolidated so we leave it empty.
    _order_list_block = (f"""
                        <INVOICEORDERLIST.LIST>
                            <BASICORDERDATE>{t_date}</BASICORDERDATE>
                            <BASICPURCHASEORDERNO>{mgrv_po_ref}</BASICPURCHASEORDERNO>
                        </INVOICEORDERLIST.LIST>""" if mgrv_po_ref else """
                        <INVOICEORDERLIST.LIST>      </INVOICEORDERLIST.LIST>""")
    invoiceorderlist_blocks = "".join(f"""
                        <INVOICEDELNOTES.LIST>
                            <BASICSHIPPINGDATE>{_dt}</BASICSHIPPINGDATE>
                            <BASICSHIPDELIVERYNOTE>{_grv}</BASICSHIPDELIVERYNOTE>
                        </INVOICEDELNOTES.LIST>""" for _grv, _dt in all_grv_pairs) + _order_list_block

    # Refine intra/inter-state from PO TAXCODE if available
    if po_gst_lookup:
        _sample_taxcode = next(iter(po_gst_lookup.values())).get("taxcode", "")
        if _sample_taxcode:
            if "GST_OT" in _sample_taxcode.upper() or "IGST" in _sample_taxcode.upper():
                is_intrastate = False
            elif "GST_IN" in _sample_taxcode.upper():
                is_intrastate = True

    inv_entries = ""
    for line in raw_lines:
        pn   = str(line.get("PARTNAME") or line.get("Part Number", "")).strip()
        pd_  = str(line.get("PDES")     or line.get("Part Description", "")).strip()
        name = resolve_po_item_name(pn, pd_)
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT") or line.get("Quantity",   0))
            rate = float(line.get("PRICE")  or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE") or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        raw_unit = str(line.get("TUNITNAME") or line.get("Unit", "")).strip()
        unit = raw_unit if raw_unit else _resolve_unit(name)

        # BRANCHNAME is on the PINVOICES main form (header_wh), not on subform lines.
        # Fall back to header_wh (branch code e.g. R01-AN) when line has no warehouse.
        line_wh = str(line.get("WARHSNAME") or line.get("Warehouse") or "").strip() or header_wh

        # ── Per-line GRV number (TRACKINGNUMBER in Tally) ─────────────────────────
        # In a multi-GRV invoice each PINVOICEITEMS row carries its own DOCNO
        # identifying which GRV/Receipt Note that item came from.
        # We read it from the subform line first; fall back to the header doc_no
        # (which only covers the single-GRV case, or is the first GRV number).
        line_doc_no = str(line.get("DOCNO") or line.get("GRV No.") or "").strip() or doc_no

        # ── GST% resolution ───────────────────────────────────────────────────────
        #
        # VAT Group column is now present directly on the Multi GRV subform (MAHI_TAXRATE),
        # so we no longer need to follow the PO reference chain as the primary source.
        #
        # Tier 1 (fastest): MAHI_TAXRATE on the MGRV line itself — read directly.
        #         Priority now populates this via the VAT Group column on the MGRV subform.
        # Tier 2: per-line ORDNAME -> fetch that exact PO -> match PARTNAME.
        #         Fallback for lines where MAHI_TAXRATE is absent/zero on the MGRV.
        # Tier 3: global_rate_map — all POs scanned; sentinel honours 0% exempt items.
        # Tier 4: back-calculate from Line GST rupee field.
        # Tier 5: proportional header VAT — absolute last resort only.
        _MISSING = object()
        total_gst_pct = 0.0
        _found        = False

        # Tier 0 — RBS_TAXCODE on the PINVOICEITEMS line (NEW primary source).
        #          e.g. "012" → 12%, "028" → 28%, "001" → exempt (0%).
        #          _decode_mahi_taxrate handles the leading-zero encoding.
        _raw_rbs = str(line.get("RBS_TAXCODE") or "").strip()
        if _raw_rbs:
            try:
                total_gst_pct = _decode_mahi_taxrate(_raw_rbs)
                _found = True
            except Exception:
                pass

        # Tier 1 — read MAHI_TAXRATE directly from MGRV line (VAT Group column)
        if not _found:
            _raw_mgrv_rate = line.get("MAHI_TAXRATE")
            if _raw_mgrv_rate is not None:
                try:
                    total_gst_pct = _decode_mahi_taxrate(_raw_mgrv_rate)
                    _found = True
                except Exception:
                    pass

        # Tier 2 — line ORDNAME -> PO form -> MAHI_TAXRATE for this PARTNAME
        #          (used only when neither RBS_TAXCODE nor MAHI_TAXRATE is on the line)
        if not _found:
            line_ordname = str(line.get("ORDNAME") or line.get("Order Number") or mgrv_po_ref or "").strip()
            if line_ordname:
                _po_lk = po_gst_lookup if line_ordname == mgrv_po_ref else _build_po_gst_lookup(line_ordname)
                for _key in (pn.upper(), pn, name.upper(), name):
                    _entry = _po_lk.get(_key)
                    if _entry is not None:
                        total_gst_pct = float(_entry.get("taxrate", 0.0)) if isinstance(_entry, dict) else float(_entry)
                        _found = True
                        break

        # Tier 3 — global map; sentinel prevents 0% items falling to Tier 4+
        if not _found:
            _g = global_rate_map.get(pn.upper(), _MISSING)
            if _g is _MISSING:
                _g = global_rate_map.get(name.upper(), _MISSING)
            if _g is not _MISSING:
                total_gst_pct = float(_g)
                _found = True

        # Tier 4 — back-calculate from Line GST rupee field
        if not _found:
            try:
                _lv = float(line.get("Line GST") or line.get("VAT") or 0)
            except Exception:
                _lv = 0.0
            if _lv > 0 and amt > 0:
                total_gst_pct = round(_lv / amt * 100, 2)
                _found = True

        # Tier 5 — proportional header VAT (absolute last resort)
        if not _found and gst_total > 0 and amt > 0:
            _lv = round(gst_total * (amt / total_line_amt), 2)
            total_gst_pct = round(_lv / amt * 100, 2) if _lv > 0 else 0.0
        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        if total_gst_pct > 0:
            if is_intrastate:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
            else:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
        else:
            rate_details = ""

        _mgrv_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch}</NAME>
                            <AMOUNT>-{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>-{amt:.2f}</AMOUNT>
                <VATASSBLVALUE>{amt:.2f}</VATASSBLVALUE>
                <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{line_wh}</DESTINATIONGODOWNNAME>
                    <TRACKINGNUMBER>{line_doc_no}</TRACKINGNUMBER>
                    <ORDERNO>{mgrv_po_ref}</ORDERNO>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                    {f"<ORDERDUEDATE>{pay_date}</ORDERDUEDATE>" if pay_date else ""}
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_PURCHASE}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    <AMOUNT>-{amt:.2f}</AMOUNT>
                    {_mgrv_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # ── Slab-wise GST ledger entries — MGRV (Input Tax Credit — debit side) ────
    #
    # FIX: Build gst_groups_mgrv by computing GST from the MGRV line's own QPRICE
    # multiplied by the tax rate sourced from the PO lookup.
    #
    # Bug that was here: enriched["CSTM_GST"] was copied from the PO line's rupee
    # amount. Since MGRV may be a partial receipt (different QPRICE than the PO),
    # _build_gst_groups would fall back to CSTM_GST (PO amount) instead of
    # computing from the MGRV QPRICE — producing wrong ledger totals that didn't
    # match the per-line RATEDETAILS computed above.
    #
    # Correct approach: stamp ONLY MAHI_TAXRATE (the %) onto enriched lines;
    # let _build_gst_groups recompute rupee amount as MGRV_QPRICE × rate/100.
    # This guarantees ledger amounts = sum of per-line GST amounts above.
    # ── Build enriched_lines for GST slab grouping ───────────────────────────
    # Now that the Multi GRV subform carries MAHI_TAXRATE directly (VAT Group column),
    # Tier 1 reads it from the line itself — no PO API call needed for most lines.
    # Stamp MAHI_TAXRATE (even 0.0 for exempt items) — _build_gst_groups skips 0%.
    # Never copy CSTM_GST from PO: MGRV qty != PO qty; let _build_gst_groups
    # recompute rupee amount as MGRV_QPRICE × MAHI_TAXRATE%, so ledger totals
    # always match RATEDETAILS exactly.
    _MISS = object()
    enriched_lines = []
    for line in raw_lines:
        _pn  = str(line.get("PARTNAME") or "").strip()
        _lpo = str(line.get("ORDNAME") or line.get("Order Number") or mgrv_po_ref or "").strip()
        enriched = dict(line)
        enriched.pop("CSTM_GST", None)
        _rate = None

        # Tier 0: RBS_TAXCODE on PINVOICEITEMS line (NEW primary source)
        _raw_rbs_e = str(line.get("RBS_TAXCODE") or "").strip()
        if _raw_rbs_e:
            try:
                _rate = _decode_mahi_taxrate(_raw_rbs_e)
            except Exception:
                pass

        # Tier 1: MAHI_TAXRATE directly on MGRV line (VAT Group column)
        if _rate is None:
            _raw_direct = line.get("MAHI_TAXRATE")
            if _raw_direct is not None:
                try:
                    _rate = _decode_mahi_taxrate(_raw_direct)
                except Exception:
                    pass

        # Tier 2: per-line ORDNAME -> PO -> MAHI_TAXRATE for this PARTNAME
        if _rate is None and _lpo:
            _lk = po_gst_lookup if _lpo == mgrv_po_ref else _build_po_gst_lookup(_lpo)
            for _k in (_pn.upper(), _pn):
                _d = _lk.get(_k)
                if _d is not None:
                    _rate = float(_d.get("taxrate", 0.0)) if isinstance(_d, dict) else float(_d)
                    break

        # Tier 3: global map (sentinel — 0.0 = exempt, no fallthrough)
        if _rate is None:
            _g = global_rate_map.get(_pn.upper(), _MISS)
            if _g is not _MISS:
                _rate = float(_g)

        # Stamp rate if found (including 0.0 for exempt items)
        if _rate is not None:
            enriched["MAHI_TAXRATE"] = _rate
        enriched_lines.append(enriched)
    gst_groups_mgrv = _build_gst_groups(enriched_lines, is_intrastate, gst_field="VAT", direction="input")

    # Last-resort fallback: if no line-level data at all, scale from Priority's
    # header VAT total (inv.get("VAT") — the actual GST the supplier charged).
    # Use this exact amount for ledger entries — don't recompute from rates.
    if not gst_groups_mgrv and gst_total > 0:
        if is_intrastate:
            _half = round(gst_total / 2, 2)
            gst_groups_mgrv = {
                _gst_ledger_name("CGST", "9", "input"): _half,
                _gst_ledger_name("SGST", "9", "input"): round(gst_total - _half, 2),
            }
        else:
            gst_groups_mgrv = {_gst_ledger_name("IGST", "18", "input"): gst_total}

    # ── Scale gst_groups_mgrv to match Priority's authoritative header VAT total ─
    # If the sum of line-computed GST differs from header VAT by more than ₹1,
    # scale proportionally so the voucher balances exactly.
    # This handles rounding differences between computed and actual GST.
    _computed_gst_sum = round(sum(gst_groups_mgrv.values()), 2)
    if gst_total > 0 and _computed_gst_sum > 0 and abs(_computed_gst_sum - gst_total) > 1.0:
        _scale = gst_total / _computed_gst_sum
        gst_groups_mgrv = {k: round(v * _scale, 2) for k, v in gst_groups_mgrv.items()}
        # Fix rounding: add/subtract remainder to largest entry
        _diff = round(gst_total - sum(gst_groups_mgrv.values()), 2)
        if _diff != 0:
            _largest_key = max(gst_groups_mgrv, key=gst_groups_mgrv.get)
            gst_groups_mgrv[_largest_key] = round(gst_groups_mgrv[_largest_key] + _diff, 2)

    gst_entries = _gst_group_ledger_entries(
        gst_groups_mgrv, is_intrastate, isdeemedpositive="Yes", sign="-"
    )

    gstin_tag = f"<PARTYGSTIN>{party_gstin}</PARTYGSTIN>" if party_gstin else ""

    # ── Taxable base = amt_owing minus GST ────────────────────────────────────
    taxable_base = round(amt_owing - gst_total, 2)

    # ── No-line fallback: pure accounting Purchase voucher ────────────────────
    # When Priority returns 0 inventory lines (subform not expanded or invoice is
    # service/expense-only), emit a flat Purchase voucher with:
    #   Dr  Purchase Account  (taxable_base)
    #   Dr  CGST/SGST or IGST (gst_total, if any)
    #   Cr  Vendor ledger     (amt_owing)
    # This is ISINVOICE=No — Tally accepts it without an inventory structure.
    if not inv_entries.strip():
        no_line_purchase = f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{LEDGER_PURCHASE}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{taxable_base:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
        xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Accounting Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <NUMBERINGSTYLE>Manual</NUMBERINGSTYLE>
                        <REFERENCE>{booknum if booknum else inv_no}</REFERENCE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>{vendor_state or COMPANY_STATE}</STATENAME>
                        <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>
                        <PLACEOFSUPPLY>{COMPANY_STATE}</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{vendor}</PARTYLEDGERNAME>
                        <PARTYNAME>{vendor}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Multi GRV Invoice from Priority ERP (no line items — accounting entry) | Receipt Note(s): {all_grv_nos_str}</NARRATION>
                        <ISINVOICE>No</ISINVOICE>
                        <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{vendor}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amt_owing:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{no_line_purchase}{gst_entries}
                        {invoiceorderlist_blocks}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return xml.strip()

    # ── Grand total: use Priority's authoritative TOTPRICE as the party ledger amount ──
    # gst_groups_mgrv has already been scaled to match gst_total (header VAT).
    # Use gst_total directly — not sum(gst_groups_mgrv) — to avoid penny differences
    # after the scale+round step above.
    computed_line_total = sum(
        float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines
    )
    # Prefer Priority's TOTPRICE as the authoritative grand total.
    # Fall back to computed_line_total + gst_total if TOTPRICE is 0 or missing.
    grand_total = round(amt_owing, 2)
    if grand_total <= 0:
        grand_total = round(computed_line_total + gst_total, 2)

    # ── Build GST ledger entries — use standard helper (same as GRV/VINV/SINV) ──
    # IMPORTANT: Do NOT use RATEOFINVOICETAX.LIST or VATEXPAMOUNT here.
    # RATEOFINVOICETAX tells Tally "apply this % to the whole invoice base" —
    # which breaks with mixed GST slabs (18%+28%+5%+0%) and causes the
    # "Tax amount does not match calculated value" warning.
    # _gst_group_ledger_entries() emits plain LEDGERENTRIES with just the amount,
    # which is what GRV, VINV and SINV all use without any warning.
    mgrv_gst_entries = _gst_group_ledger_entries(
        gst_groups_mgrv, is_intrastate, isdeemedpositive="Yes", sign="-"
    )

    # ── Normal path: inventory invoice ────────────────────────────────────────
    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <NUMBERINGSTYLE>Manual</NUMBERINGSTYLE>
                        <REFERENCE>{booknum if booknum else inv_no}</REFERENCE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>{vendor_state or COMPANY_STATE}</STATENAME>
                        <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>
                        <PLACEOFSUPPLY>{COMPANY_STATE}</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{vendor}</PARTYLEDGERNAME>
                        <PARTYNAME>{vendor}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Multi GRV Invoice from Priority ERP | Receipt Note(s): {all_grv_nos_str}</NARRATION>
                        <ISINVOICE>Yes</ISINVOICE>
                        <ISELIGIBLEFORITC>Yes</ISELIGIBLEFORITC>
                        <DIFFACTUALQTY>Yes</DIFFACTUALQTY>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{vendor}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{grand_total:.2f}</AMOUNT>
                            <BILLALLOCATIONS.LIST>
                                <NAME>{booknum if booknum else inv_no}</NAME>
                                <BILLTYPE>New Ref</BILLTYPE>
                                <AMOUNT>{grand_total:.2f}</AMOUNT>
                                {f"<DUEDATE>{pay_date}</DUEDATE>" if pay_date else ""}
                            </BILLALLOCATIONS.LIST>
                        </LEDGERENTRIES.LIST>{mgrv_gst_entries}
                        {invoiceorderlist_blocks}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()

def run_mgrv_push(invoices: list, dry_run: bool, source: str) -> list:
    """Push Final Multi GRV invoices to Tally as Purchase Invoice vouchers (ISINVOICE=Yes)."""
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(invoices)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing vendor ledgers & stock items in Tally…")
        # Build the global tax rate map once for all invoices — avoids repeated API calls per invoice
        _all_lines_check = [l for rec in invoices for l in (rec.get(MGRV_SUBFORM) or [])]
        _all_rbs_covered = all(
            str(l.get("RBS_TAXCODE") or "").strip() != "" for l in _all_lines_check
        ) if _all_lines_check else False
        global_rate_map = {} if _all_rbs_covered else _build_partname_taxrate_map()
        for rec in invoices:
            v = rec.get("Vendor Name") or rec.get("CDES", "")
            if v: ensure_vendor_ledger(v, "Sundry Creditors")
            _is_intra = _detect_intrastate(rec)
            _lines_for_si = rec.get(MGRV_SUBFORM) or []
            for line in _lines_for_si:
                item_name = resolve_po_item_name(line.get("PARTNAME", ""), line.get("PDES", ""))
                if item_name:
                    # Resolve GST rate — Tier 0: RBS_TAXCODE, Tier 1: MAHI_TAXRATE, Tier 2: global map
                    _pn = str(line.get("PARTNAME") or "").strip()
                    _raw_rbs_si = str(line.get("RBS_TAXCODE") or "").strip()
                    if _raw_rbs_si:
                        _rate = _decode_mahi_taxrate(_raw_rbs_si)
                    elif line.get("MAHI_TAXRATE") is not None:
                        _rate = _decode_mahi_taxrate(line.get("MAHI_TAXRATE"))
                    else:
                        _g = global_rate_map.get(_pn.upper())
                        _rate = float(_g) if _g is not None else 0.0
                    ensure_stock_item(item_name, "", gst_rate=_rate, is_intrastate=_is_intra)
        status_ph.info("⚙ Step 2/2 — Pushing Purchase Invoice vouchers to Tally…")
    for i, rec in enumerate(invoices):
        inv_no  = rec.get("BOOKNUM") or rec.get("Invoice No.") or rec.get("IVNUM", "?")  # use supplier invoice no. (BOOKNUM) for display
        status  = rec.get("Status")      or rec.get("STATDES", "")
        vendor  = rec.get("Vendor Name") or rec.get("CDES", "")
        amount  = rec.get("Amount Owing") or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{inv_no}` ({i+1}/{total})…")
        xml = build_mgrv_xml(rec)
        if dry_run:
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Vendor": vendor, "Amount": fmt_inr(amount),
                            "Tally Type": "Purchase (Invoice)", "Result": "🧪 Dry run — XML built, not pushed",
                            "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S")})
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({"Source": source, "Invoice No": inv_no, "Status": status,
                            "Vendor": vendor, "Amount": fmt_inr(amount),
                            "Tally Type": "Purchase (Invoice)",
                            "Result": f"{'✅' if ok else '❌'} {msg}",
                            "XML": xml, "Tally Response": tally_raw,
                            "Timestamp": datetime.now().strftime("%H:%M:%S")})
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE: MULTI SHIPMENT INVOICE  (CINVOICES — Final status → Tally Sales Invoice)
# ═══════════════════════════════════════════════════════════════════════════════
#  Priority forms:
#    Main form  : CINVOICES
#    Sub-form   : CINVOICEITEMS
#  Shipment doc numbers are carried per line in CINVOICEITEMS.DOCCODE.
#  Multiple distinct DOCCODE values → multiple INVOICEDELNOTES.LIST blocks in
#  Tally's Dispatch Details (Delivery Note No(s.) field).
#  Each inventory line also carries TRACKINGNUMBER = its own DOCCODE so Tally
#  links every item back to the correct Shipment document.
# ═══════════════════════════════════════════════════════════════════════════════

# ─── MULTI SHIPMENT INVOICE CONFIG ────────────────────────────────────────────
MSINV_FORM        = "CINVOICES"
MSINV_SUBFORM     = "CINVOICEITEMS_SUBFORM"
MSINV_PUSH_STATUS = "Final"

MSINV_HEADER_MAP = {
    "CUSTNAME":   "Customer No.",
    "CDES":       "Customer Name",
    "IVDATE":     "Date",
    "CURDATE":    "Date",            # fallback
    "IVNUM":      "Invoice No.",
    "ORDNAME":    "Order Number",
    "QPRICE":     "Total Before Discount",
    "PERCENT":    "Overall Discount (%)",
    "DISPRICE":   "Price After Discount",
    "VAT":        "GST",
    "TOTPRICE":   "Grand Total",
    "STATDES":    "Status",
    "WARHSNAME":  "Warehouse",
    "BRANCHNAME": "Branch",          # header-level branch code (e.g. R01-AN) → Tally GODOWNNAME
    "TAXCODE":    "VAT Code",
    "PARTYVAT":   "Customer GSTIN",
    "STATENAME":  "Customer State",
    "CODE":       "Currency",
    "DOCNO":      "Shipment No.",    # header-level shipment number (single shipment direct conversion)
    "DNAME":      "Shipment No. Alt", # alternate header shipment field
}

MSINV_LINE_MAP = {
    "PARTNAME":    "Part Number",
    "PDES":        "Part Description",
    "TQUANT":      "Quantity",
    "TUNITNAME":   "Unit",
    "PRICE":       "Unit Price",
    "PERCENT":     "Discount %",
    "QPRICE":      "Total Price",
    "VAT":         "Line GST",
    "WARHSNAME":   "Warehouse",
    "RBS_TAXCODE": "VAT Group",      # GST slab code per line (authoritative for msinv)
                                     # "001"=exempt/nil, "005"=5%, "012"=12%, "028"=28%
    "MAHI_TAXRATE":"VAT Group Alt",  # retained as fallback; may not be populated on CINVOICEITEMS
    "DOCNO":       "Shipment No.",   # Per-line Shipment document number -> TRACKINGNUMBER
    "DOCCODE":     "Shipment No. (alt)",  # alternate field name -- fallback
                                     # -> INVOICEDELNOTES.LIST in Dispatch Details
}

MSINV_PUSH_STATUSES = {"Final"}

# ??? SHIPPING DOCUMENTS (DOCUMENTS_D) CONFIG ??????????????????????????????????
SH_FORM          = "DOCUMENTS_D"

# ── Line-items subform ────────────────────────────────────────────────────────
SH_ITEMS_SUBFORM = "TRANSORDER_D_SUBFORM"  # mirrors GRV: TRANSORDER_P_SUBFORM

# ── SO-reference subform — DOCORDI holds originating SO links ─────────────────
SH_SO_SUBFORM_CANDIDATES = [
    "DOCORDI",
    "DOCORD_SUBFORM",
    "DOCORDI_SUBFORM",
    "DOCORDLINK",
]
SH_SO_SUBFORM = None   

SH_STATUS_GATE = "Final"

TALLY_URL         = os.environ.get("TALLY_URL", "http://localhost:9000")
TALLY_COMPANY     = os.environ.get("TALLY_COMPANY", "Rishi's Test Zone")
TALLY_COMPANY_XML = TALLY_COMPANY.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

COMPANY_STATE = "Maharashtra"
LEDGER_SALES  = "Sales Account"

SH_HEADER_MAP = {
    "CUSTNAME":    "Customer No.",
    "CDES":        "Customer Name",
    "DOCNO":       "Doc. Number",
    "REPNAME":     "Rep's Doc. No.",
    "STATDES":     "Status",
    "DOCDATE":     "Doc. Date",
    "ORDNAME":     "Sales Order",
    "WARHSNAME":   "Sending Warehouse",
    "WARHSDES":    "Send Warehouse Desc",
    "LOCNAME":     "Shipping Bin",
    "DISTRDATE":   "Date",             # Delivery/distribution date → primary date for filtering
    "LORRYNO":     "Lorry No.",
    "SHIPPERNAME": "Shipper/Driver Name",
    "TRACKNO":     "Tracking Number",
    "QPRICE":      "Total Before Discount",
    "PERCENT":     "% Overall Discount",
    "DISPRICE":    "Price After Discount",
    "VAT":         "VAT",
    "TOTPRICE":    "Final Price",
    "CURRENCY":    "Currency",
    "VATCODE":     "VAT Code",
    "TOTQUANT":    "Qty of Items",
    "BILLED":      "Billed",
    "PRINTED":     "Printed",
    "BRANCHNAME":  "Branch",        # header-level branch code → Tally COSTCENTRENAME
}

SH_LINE_MAP = {
    "PARTNAME":     "Part Number",
    "PDES":         "Part Description",
    "TQUANT":       "Quantity",
    "TUNITNAME":    "Unit",
    "PRICE":        "Unit Price",
    "VPRICE":       "Price After Disc",
    "QPRICE":       "Total Price",
    "MAHI_TAXRATE": "GST Slab Rate",
    "RBS_TAXCODE":  "VAT Group Code",
    "WARHSNAME":    "Warehouse",
    "LOCNAME":      "Bin",
    "ORDNAME":      "SO Ref",
    "DISTRDATE":    "Delivery Date",
}

# ?? Session-state keys for Shipping Documents ?????????????????????????????????
for _sh_key, _sh_default in [
    ("sh_tally_nos_override", set()),
    ("sh_pipeline_raw",       []),
    ("sh_safe_doc_nos",       set()),
    ("sh_last_push_results",  []),
]:
    if _sh_key not in st.session_state:
        st.session_state[_sh_key] = _sh_default


_SH_ITEMS_EXPAND_CANDIDATES = [
    "TRANSORDER_D_SUBFORM",   # confirmed pattern: GRV uses TRANSORDER_P_SUBFORM
    "TRANSORDER_D",           # fallback without _SUBFORM suffix
    "DORDERITEMS_SUBFORM",
    "TRANSORDER",
]



def _sh_doc_key(value) -> str:
    return str(value or "").strip()


def _sh_tally_date(s: str, fallback_today: bool = True) -> str:
    s = str(s or "").strip()
    if not s or s in ("None", "nan", ""):
        return datetime.today().strftime("%Y%m%d") if fallback_today else ""

    m = re.search(r"/Date\((\d+)", s)
    if m:
        try:
            return datetime.utcfromtimestamp(int(m.group(1)) / 1000).strftime("%Y%m%d")
        except Exception:
            pass

    try:
        serial = int(float(s))
        if 20000 < serial < 60000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).strftime("%Y%m%d")
    except (ValueError, TypeError):
        pass

    for fmt in ("%d %b %Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except (ValueError, TypeError):
            pass
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(fmt))], fmt).strftime("%Y%m%d")
        except Exception:
            pass

    return datetime.today().strftime("%Y%m%d") if fallback_today else ""


def _sh_paginate(url: str, headers: dict, raise_on_error: bool = False) -> tuple[list, int | None]:
    records, page_no, expected_count = [], 1, None
    while url:
        try:
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            d = r.json()
            if page_no == 1:
                expected_count = d.get("@odata.count")
            page_records = d.get("value", [])
            records.extend(page_records)
            print(f"[PAGE {page_no}] +{len(page_records)} rows ? total {len(records)}")
            url = d.get("@odata.nextLink") or d.get("odata.nextLink") or d.get("nextLink")
            page_no += 1
        except Exception as e:
            msg = f"Pagination failed on Page {page_no}: {e}"
            print(f"[PAGINATION ERROR] {msg}")
            if raise_on_error:
                raise RuntimeError(msg) from e
            st.error(f"OData Extraction Fault: {msg}")
            break
    print(f"[COMPLETE] Total records downloaded: {len(records)}")
    return records, expected_count


@st.cache_data(ttl=3600, show_spinner=False)
def _sh_fetch_vat_group_map() -> dict:
    hdrs = _auth_headers()
    url  = f"{PRIORITY_BASE}/VATGROUPS?$select=VATGROUP,VATDES"
    mapping = {}
    try:
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        for row in r.json().get("value", []):
            code = str(row.get("VATGROUP") or "").strip()
            desc = str(row.get("VATDES")   or "").strip()
            if not code:
                continue
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", desc)
            mapping[code] = float(m.group(1)) if m else 0.0
    except Exception:
        pass
    return mapping


def _sh_taxcode_to_rate(taxcode) -> float:
    code = str(taxcode or "").strip()
    if not code:
        return 0.0
    vat_map = _sh_fetch_vat_group_map()
    if code in vat_map:
        return vat_map[code]
    try:
        return float(int(code))
    except (TypeError, ValueError):
        return 0.0


def _sh_build_gst_groups(raw_lines: list, is_intrastate: bool, direction: str = "output") -> dict:
    groups = {}
    for line in raw_lines:
        try:
            amt      = float(line.get("QPRICE") or line.get("Total Price") or 0)
            raw_rate = line.get("MAHI_TAXRATE") or line.get("GST Slab Rate")
            taxrate  = float(raw_rate) if raw_rate else _sh_taxcode_to_rate(
                line.get("RBS_TAXCODE") or line.get("VAT Group Code")
            )
        except Exception:
            continue
        if taxrate <= 0 or amt <= 0:
            continue
        cstm_gst = line.get("CSTM_SOGST") or line.get("Line GST")
        try:
            line_gst = float(cstm_gst) if cstm_gst not in (None, "", "None", "nan") else None
        except (TypeError, ValueError):
            line_gst = None
        if not line_gst:
            line_gst = round(amt * taxrate / 100, 2)
        line_gst = round(line_gst, 2)
        if is_intrastate:
            h = taxrate / 2
            hs = f"{h:g}"
            ha = round(line_gst / 2, 2)
            cgst_k = _gst_ledger_name("CGST", hs, direction)
            sgst_k = _gst_ledger_name("SGST", hs, direction)
            groups[cgst_k] = round(groups.get(cgst_k, 0.0) + ha, 2)
            groups[sgst_k] = round(groups.get(sgst_k, 0.0) + ha, 2)
        else:
            k = _gst_ledger_name("IGST", f"{taxrate:g}", direction)
            groups[k] = round(groups.get(k, 0.0) + line_gst, 2)
    return groups


def _sh_gst_ledger_entries(gst_groups: dict) -> str:
    out = ""
    for name in sorted(gst_groups):
        amt = gst_groups[name]
        if amt <= 0:
            continue
        out += f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{name}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{amt:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
    return out


def _sh_tally_master_exists(name: str, account_type: str) -> bool:
    xml = (
        f"<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>"
        f"<BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME>"
        f"<STATICVARIABLES><SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>"
        f"<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
        f"<ACCOUNTTYPE>{account_type}</ACCOUNTTYPE>"
        f"</STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
    )
    try:
        resp = requests.post(
            TALLY_URL, data=xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"}, timeout=5,
        )
        return bool(re.search(rf"<NAME>\s*{re.escape(name)}\s*</NAME>", resp.text, re.I))
    except Exception:
        return False


def _sh_ensure_debtor_ledger(name: str):
    if not name or _sh_tally_master_exists(name, "Ledgers"):
        return
    xml = (
        f"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>"
        f"<BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME>"
        f"<STATICVARIABLES><SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>"
        f"</STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE>"
        f'<LEDGER NAME="{name}" ACTION="Create">'
        f"<NAME>{name}</NAME><PARENT>Sundry Debtors</PARENT>"
        f"<ISBILLWISEON>Yes</ISBILLWISEON>"
        f"</LEDGER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
    )
    try:
        requests.post(TALLY_URL, data=xml.encode("utf-8"),
                      headers={"Content-Type": "application/xml"}, timeout=4)
    except Exception:
        pass


def _sh_ensure_stock_item(name: str):
    if not name or _sh_tally_master_exists(name, "Stock Items"):
        return
    xml = (
        f"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>"
        f"<BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME>"
        f"<STATICVARIABLES><SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>"
        f"</STATICVARIABLES></REQUESTDESC><REQUESTDATA><TALLYMESSAGE>"
        f'<STOCKITEM NAME="{name}" ACTION="Create">'
        f"<NAME>{name}</NAME><PARENT>Finished Goods</PARENT>"
        f"</STOCKITEM></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
    )
    try:
        requests.post(TALLY_URL, data=xml.encode("utf-8"),
                      headers={"Content-Type": "application/xml"}, timeout=4)
    except Exception:
        pass


def _collect_so_refs(sh: dict, resolved_so_subform: str | None) -> list[str]:
    """
    STRICT SUB-FORM RULE:
    Returns an ordered, deduplicated list of Sales Order numbers for a shipment
    extracted ONLY from the line-item subforms (DOCORDI and TRANSORDER_D).
    The header is completely ignored.
    """
    seen: set[str] = set()
    refs: list[str] = []

    def _add(val):
        v = str(val or "").strip()
        if v and v not in seen:
            seen.add(v)
            refs.append(v)

    # ── Tier 1: DOCORDI subform ───────────────────────────────────────────────
    docordi_rows = []
    if resolved_so_subform:
        docordi_rows = sh.get(resolved_so_subform) or []
    if not docordi_rows:
        for _cand in SH_SO_SUBFORM_CANDIDATES:
            _rows = sh.get(_cand)
            if _rows:
                docordi_rows = _rows
                break
    for row in docordi_rows:
        _add(row.get("ORDNAME") or row.get("ORDFNAME") or row.get("ORD"))

    # ── Tier 2: TRANSORDER_D line ORDNAMEs ───────────────────────────────────
    if not refs:
        for ln in (sh.get(SH_ITEMS_SUBFORM) or []):
            _add(ln.get("ORDNAME"))

    return refs



def build_sh_xml(sh: dict, resolved_so_subform: str | None = None) -> tuple[str, dict]:
    """
    Compiles a Tally Delivery Note XML from a DOCUMENTS_D record.
    Returns (xml_string, diagnostics_dict).
    """
    doc_no    = sh.get("Doc. Number")            or sh.get("DOCNO",    "")
    raw_date  = sh.get("Date")                   or sh.get("DOCDATE",  "")
    customer  = sh.get("Customer Name")          or sh.get("CDES",     "")
    grand_tot = float(sh.get("Final Price")      or sh.get("TOTPRICE") or 0)
    gst_total = float(sh.get("VAT")              or 0)
    wh_name   = str(sh.get("Sending Warehouse") or sh.get("WARHSNAME", "")).strip()
    lorry_no  = str(sh.get("Lorry No.")          or sh.get("LORRYNO",  "")).strip()
    track_no  = str(sh.get("Tracking Number")    or sh.get("TRACKNO",  "")).strip()
    cust_po   = str(sh.get("Rep's Doc. No.")     or sh.get("REPNAME",  "")).strip()
    branch    = str(
        sh.get("BRANCHNAME") or sh.get("Branch") or
        sh.get("BRANCH")     or sh.get("BRANCHDES") or ""
    ).strip()

    is_intrastate = _detect_intrastate(sh)
    raw_lines     = sh.get(SH_ITEMS_SUBFORM) or []

    # ── Multi-SO collection (Strictly Sub-forms) ─────────────────────────────
    so_refs = _collect_so_refs(sh, resolved_so_subform)
    so_ref  = ", ".join(so_refs)   

    # ── Delivery date ────────────────────────────────────────────────────────
    # Priority field priority: DUEDATEOI (subform) > DISTRDATE (header/line)
    raw_due = sh.get("Delivery Date") or sh.get("DISTRDATE") or ""
    if not raw_due:
        for ln in raw_lines:
            dd = str(ln.get("DUEDATEOI") or ln.get("DISTRDATE") or "").strip()
            if dd and dd not in ("None", "nan"):
                raw_due = dd
                break

    t_date     = _sh_tally_date(str(raw_date), fallback_today=True)
    t_del_date = _sh_tally_date(str(raw_due),  fallback_today=False) if raw_due else ""

    # ── Per-SO delivery date map ─────────────────────────────────────────────
    so_date_map: dict[str, str] = {}
    for ln in raw_lines:
        ln_so = str(ln.get("ORDNAME") or "").strip()
        if not ln_so:
            continue
        ln_dd = str(ln.get("DISTRDATE") or "").strip()
        so_date_map[ln_so] = _sh_tally_date(ln_dd, fallback_today=False) or t_del_date or t_date
    for s in so_refs:
        if s and s not in so_date_map:
            so_date_map[s] = t_del_date or t_date

    # ── Diagnostics snapshot ─────────────────────────────────────────────────
    docordi_rows_count = 0
    if resolved_so_subform:
        docordi_rows_count = len(sh.get(resolved_so_subform) or [])
    if not docordi_rows_count:
        for _cand in SH_SO_SUBFORM_CANDIDATES:
            _r = sh.get(_cand)
            if _r:
                docordi_rows_count = len(_r)
                break

    diag = {
        "Header ORDNAME":         sh.get("ORDNAME")    or sh.get("Sales Order")    or "",
        "Header DISTRDATE":       sh.get("DISTRDATE")  or sh.get("Delivery Date")  or "",
        "Item ORDNAME (first)":   (raw_lines[0].get("ORDNAME")   or "") if raw_lines else "",
        "Item DISTRDATE (first)": (raw_lines[0].get("DISTRDATE") or "") if raw_lines else "",
        "DOCORDI Rows":           str(docordi_rows_count),
        "SO Refs Collected":      so_ref or "(none)",
        "SO Count":               str(len(so_refs)),
        "Resolved Delivery Date": str(raw_due) if raw_due else "(blank → Not Applicable)",
        "DUEDATEOI Source":        "subform line" if any(str(ln.get("DUEDATEOI") or "").strip() not in ("", "None", "nan") for ln in raw_lines) else "not found",
        "DOCDATE Raw Value":      str(sh.get("Date") or sh.get("DOCDATE") or ""),
        "Final Tally Date":       t_date,
        "GST Mode":               "Intrastate (CGST+SGST)" if is_intrastate else "Interstate (IGST)",
        "VATCODE":                str(sh.get("VAT Code") or sh.get("VATCODE") or ""),
        "Lorry No.":              lorry_no,
        "Tracking No.":           track_no,
        "SO Subform Used":        resolved_so_subform or "(none — header/line fallback)",
    }

    _sh_ensure_debtor_ledger(customer)
    for line in raw_lines:
        pn = str(line.get("PARTNAME") or "").strip()
        if pn:
            _sh_ensure_stock_item(pn)

    inv_entries   = ""
    line_ordnames = [str(ln.get("ORDNAME") or "").strip() for ln in raw_lines]

    for idx, line in enumerate(raw_lines):
        name = str(line.get("PARTNAME") or line.get("Part Number", "")).strip()
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT") or line.get("Quantity",    0))
            rate = float(line.get("PRICE")  or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE") or line.get("Total Price", 0))
            raw_slab = line.get("MAHI_TAXRATE") or line.get("GST Slab Rate")
            slab = float(raw_slab) if raw_slab else _sh_taxcode_to_rate(
                line.get("RBS_TAXCODE") or line.get("VAT Group Code")
            )
        except Exception:
            qty = rate = amt = slab = 0.0

        unit    = str(line.get("TUNITNAME") or line.get("Unit", "Nos")).strip()
        bin_loc = str(line.get("LOCNAME")   or line.get("Bin", "")).strip()
        
        # ── Per-line due date: DUEDATEOI from subform, fallback to doc-level ──
        line_due_raw = str(line.get("DUEDATEOI") or line.get("DISTRDATE") or "").strip()
        line_due_raw = line_due_raw if line_due_raw not in ("None", "nan", "") else ""
        line_due_date = _sh_tally_date(line_due_raw, fallback_today=False) if line_due_raw else t_del_date
        orderduedate_tag = f"<ORDERDUEDATE>{line_due_date}</ORDERDUEDATE>" if line_due_date else ""
        # STRICT SUB-FORM ALLOCATION
        orderno = str(line_ordnames[idx]).strip() if idx < len(line_ordnames) else ""
        
        godown  = bin_loc if bin_loc and bin_loc not in ("0", "") else (wh_name or "Main Location")

        rate_details = ""
        if slab > 0:
            if is_intrastate:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATE>{round(slab/2, 2)}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATE>{round(slab/2, 2)}</GSTRATE>
                </RATEDETAILS.LIST>"""
            else:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATE>{slab}</GSTRATE>
                </RATEDETAILS.LIST>"""

        _sh_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{_xml_text(branch)}</NAME>
                            <AMOUNT>{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{_xml_text(name)}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>{amt:.2f}</AMOUNT>
                <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{_xml_text(godown)}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{_xml_text(godown)}</DESTINATIONGODOWNNAME>
                    <INDENTNO>&#4; Not Applicable</INDENTNO>
                    <ORDERNO>{_xml_text(orderno)}</ORDERNO>
                    <TRACKINGNUMBER>{_xml_text(doc_no)}</TRACKINGNUMBER>
                    {orderduedate_tag}
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_SALES}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    {_sh_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    gst_groups = _sh_build_gst_groups(raw_lines, is_intrastate, direction="output")
    if not gst_groups and gst_total > 0:
        if is_intrastate:
            _half = round(gst_total / 2, 2)
            gst_groups = {
                _gst_ledger_name("CGST", "9", "output"): _half,
                _gst_ledger_name("SGST", "9", "output"): round(gst_total - _half, 2),
            }
        else:
            gst_groups = {_gst_ledger_name("IGST", "18", "output"): gst_total}

    gst_entries   = _sh_gst_ledger_entries(gst_groups)
    narration_tag = (
        f"<NARRATION>SO Ref(s): {_xml_text(so_ref)}</NARRATION>" if so_ref else ""
    )
    due_date_tag  = f"<REFERENCEDATE>{t_del_date}</REFERENCEDATE>" if t_del_date else ""

    invoice_order_entries = ""
    for so_num in dict.fromkeys(s for s in so_refs if s):
        so_ord_date = so_date_map.get(so_num, t_date)
        invoice_order_entries += f"""
                        <INVOICEORDERLIST.LIST>
                            <BASICORDERDATE>{so_ord_date}</BASICORDERDATE>
                            <ORDERTYPE>Sales Order</ORDERTYPE>
                            <BASICPURCHASEORDERNO>{_xml_text(so_num)}</BASICPURCHASEORDERNO>
                        </INVOICEORDERLIST.LIST>"""

    xml = f"""<ENVELOPE>
    <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Delivery Note" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        {due_date_tag}
                        <VOUCHERTYPENAME>Delivery Note</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{_xml_text(doc_no)}</VOUCHERNUMBER>
                        <REFERENCE>{_xml_text(doc_no)}</REFERENCE>
                        {narration_tag}
                        <BASICSHIPDELIVERYNOTE>{_xml_text(cust_po)}</BASICSHIPDELIVERYNOTE>
                        <BASICSHIPPINGCOMPANY>{_xml_text(lorry_no)}</BASICSHIPPINGCOMPANY>
                        <BASICSHIPDOCUMENTNO>{_xml_text(track_no)}</BASICSHIPDOCUMENTNO>
                        <BASICBUYERBILLNO>{_xml_text(doc_no)}</BASICBUYERBILLNO>
                        <BASICBUYERBILLDATE>{t_date}</BASICBUYERBILLDATE>
                        <BASICBUYERNAME>{_xml_text(customer)}</BASICBUYERNAME>
                        <CONSIGNEESTATE>{COMPANY_STATE}</CONSIGNEESTATE>
                        <PARTYLEDGERNAME>{_xml_text(customer)}</PARTYLEDGERNAME>
                        <PARTYNAME>{_xml_text(customer)}</PARTYNAME>
                        <ISINVOICE>No</ISINVOICE>
                        <DIFFACTUALQTY>Yes</DIFFACTUALQTY>
                        <VCHENTRYMODE>Item Invoice</VCHENTRYMODE>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{_xml_text(branch)}</COSTCENTRENAME>' if branch else ''}
                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{_xml_text(customer)}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{gst_entries}
                        <INVOICEDELNOTES.LIST></INVOICEDELNOTES.LIST>
                        {invoice_order_entries}
                        <INVOICEINDENTLIST.LIST></INVOICEINDENTLIST.LIST>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>""".strip()

    return xml, diag



def query_tally_delivery_register() -> set:
    today    = datetime.today()
    fy_start = datetime(today.year if today.month >= 4 else today.year - 1, 4, 1)
    fy_end   = datetime(fy_start.year + 1, 3, 31)
    xml = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>Voucher Register</REPORTNAME>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      <SVFROMDATE>{fy_start.strftime('%Y%m%d')}</SVFROMDATE>
      <SVTODATE>{fy_end.strftime('%Y%m%d')}</SVTODATE>
      <VOUCHERTYPENAME>Delivery Note</VOUCHERTYPENAME>
    </STATICVARIABLES>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
    nos = set()
    try:
        r = requests.post(
            TALLY_URL, data=xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"}, timeout=10,
        )
        if r.status_code == 200:
            for m in re.finditer(r"<VOUCHERNUMBER>\s*(.*?)\s*</VOUCHERNUMBER>", r.text, re.I | re.S):
                v = _sh_doc_key(m.group(1))
                if v:
                    nos.add(v)
    except Exception:
        pass
    return nos



def run_sh_push(records: list, resolved_so_subform: str | None, dry_run: bool = False) -> list:
    results = []
    bar     = st.progress(0, text="Synchronizing with Tally Gateway...")
    total   = len(records)
    for idx, rec in enumerate(records):
        doc_no   = rec.get("DOCNO", "UNKNOWN")
        customer = rec.get("CDES",  "UNKNOWN")
        amount   = fmt_inr(rec.get("TOTPRICE", 0))
        try:
            xml_payload, diag = build_sh_xml(rec, resolved_so_subform)
            if dry_run:
                status_msg = "🟡 Dry Run (Not Pushed)"
                tally_type = "Preview"
            else:
                _, status_msg, _ = push_to_tally(xml_payload)
                tally_type = "Delivery Note"
            results.append({
                "Doc. No":     doc_no,
                "Customer":    customer,
                "Amount":      amount,
                "Tally Type":  tally_type,
                "Result":      status_msg,
                "Timestamp":   datetime.now().strftime("%H:%M:%S"),
                "XML":         xml_payload,
                "Diagnostics": diag,
            })
            if not dry_run:
                time.sleep(0.1)
        except Exception as e:
            results.append({
                "Doc. No":     doc_no,
                "Customer":    customer,
                "Amount":      amount,
                "Tally Type":  "Fault",
                "Result":      f"Compilation Error: {e}",
                "Timestamp":   datetime.now().strftime("%H:%M:%S"),
                "XML":         "Failed to compile.",
                "Diagnostics": {},
            })
        bar.progress((idx + 1) / total, text=f"Processing {idx + 1} of {total}...")
    time.sleep(0.4)
    bar.empty()
    return results



@st.cache_data(ttl=3600, show_spinner=False)
def _probe_sh_so_subform() -> str | None:
    hdrs = _auth_headers()
    for candidate in SH_SO_SUBFORM_CANDIDATES:
        test_url = f"{PRIORITY_BASE}/{SH_FORM}?$expand={candidate}&$top=1"
        try:
            r = requests.get(test_url, headers=hdrs, timeout=15)
            if r.status_code == 200:
                print(f"[SO SUBFORM PROBE] '{candidate}' accepted.")
                return candidate
        except Exception:
            continue
    print("[SO SUBFORM PROBE] All candidates failed — SO refs via line/header fallback.")
    return None



@st.cache_data(ttl=300, show_spinner=False)
def fetch_live_sh_data() -> tuple[list, int | None, str, str | None]:
    hdrs           = _auth_headers()
    base           = f"{PRIORITY_BASE}/{SH_FORM}"
    so_subform     = _probe_sh_so_subform()   

    for candidate in _SH_ITEMS_EXPAND_CANDIDATES:
        # Try 1: items subform + SO subform combined
        # Try 2: items subform alone (SO refs fall back to header/line ORDNAME)
        urls_to_try = []
        if so_subform:
            urls_to_try.append((f"{base}?$expand={candidate},{so_subform}&$count=true&$top=500", so_subform))
        urls_to_try.append((f"{base}?$expand={candidate}&$count=true&$top=500", None))

        for url, active_so_subform in urls_to_try:
            try:
                r = requests.get(url, headers=hdrs, timeout=30)
                if r.status_code == 200 and "value" in r.json():
                    print(f"[EXPAND OK] accepted: {url.split('?')[1][:80]}")
                    records, count = _sh_paginate(url, hdrs, raise_on_error=True)
                    return records, count, candidate, active_so_subform
                print(f"[EXPAND FAIL] '{candidate}' → HTTP {r.status_code}")
            except Exception as e:
                print(f"[EXPAND ERROR] '{candidate}' → {e}")

    print("[FALLBACK] Fetching DOCUMENTS_D without $expand (header-only).")
    url = f"{base}?$count=true&$top=500"
    records, count = _sh_paginate(url, hdrs)
    return records, count, "(none — expand failed)", None



def build_sh_header_df(raw: list, expand_name: str, resolved_so_subform: str | None) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    enriched = []
    for rec in raw:
        rec   = dict(rec)
        lines = rec.get(expand_name) or rec.get(SH_ITEMS_SUBFORM) or []

        if not str(rec.get("ORDNAME") or "").strip():
            so_refs = _collect_so_refs(rec, resolved_so_subform)
            if so_refs:
                rec["ORDNAME"] = ", ".join(so_refs)

        if not str(rec.get("DISTRDATE") or "").strip():
            for ln in lines:
                d = str(ln.get("DISTRDATE") or "").strip()
                if d and d not in ("None", "nan"):
                    rec["DISTRDATE"] = d
                    break
        enriched.append(rec)

    df = pd.DataFrame(enriched)
    drop_cols = [c for c in df.columns if c in [expand_name, SH_ITEMS_SUBFORM]
                 or c in SH_SO_SUBFORM_CANDIDATES]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")
    df = df.rename(columns={k: v for k, v in SH_HEADER_MAP.items() if k in df.columns})
    df = _parse_dates(df, "Date", "Doc. Date")
    return _to_num(df, "Total Before Discount", "VAT", "Final Price", "Qty of Items")


def build_sh_lines_df(raw: list, expand_name: str) -> pd.DataFrame:
    rows = []
    for sh in raw:
        lines  = sh.get(expand_name) or sh.get(SH_ITEMS_SUBFORM) or []
        hdr_so = str(sh.get("ORDNAME") or "").strip()
        base   = {
            "Doc. Number":   sh.get("DOCNO"),
            "Customer Name": sh.get("CDES"),
            "Date":          sh.get("DOCDATE"),
            "Status":        sh.get("STATDES"),
        }
        for line in lines:
            rows.append({
                **base,
                "SO Ref": str(line.get("ORDNAME") or "").strip() or hdr_so,
                **{v: line.get(k) for k, v in SH_LINE_MAP.items() if k != "ORDNAME"},
            })
    if not rows:
        return pd.DataFrame()
    return _to_num(
        _parse_dates(pd.DataFrame(rows), "Date"),
        "Quantity", "Unit Price", "Price After Disc", "Total Price", "GST Slab Rate",
    )


def _sh_tally_match_label(doc_no, status: str) -> str:
    dk = _sh_doc_key(doc_no)
    if dk in st.session_state.get("sh_tally_nos_override", set()):
        return "Already in Tally"
    if str(status or "").strip().upper() != SH_STATUS_GATE.upper():
        return f"Status Blocked ({status})"
    return "Safe to Sync"



@st.cache_data(ttl=300, show_spinner=False)
def fetch_msinv_invoices():
    """Fetch Final Multi Shipment Invoices from Priority CINVOICES with line items.

    Attempt order:
      1. With $select + $expand  (fastest, explicit fields)
      2. Without $select, with $expand  (safest — works even if a field name differs)
      3. Without $expand  (headers only — last resort)
    """
    hdrs = _auth_headers()
    header_select = (
        "CUSTNAME,CDES,IVDATE,CURDATE,IVNUM,ORDNAME,DOCNO,DNAME,"
        "QPRICE,PERCENT,DISPRICE,VAT,TOTPRICE,STATDES,WARHSNAME,BRANCHNAME,"
        "TAXCODE,PARTYVAT,STATENAME,CODE"
    )
    attempts = [
        f"{PRIORITY_BASE}/{MSINV_FORM}?$select={header_select}&$expand={MSINV_SUBFORM}&$top=500",
        f"{PRIORITY_BASE}/{MSINV_FORM}?$expand={MSINV_SUBFORM}&$top=500",
        f"{PRIORITY_BASE}/{MSINV_FORM}?$top=500",
    ]
    for url in attempts:
        try:
            records = _paginate(url, hdrs)
            if records is not None:
                has_lines = any(
                    isinstance(r.get(MSINV_SUBFORM), list) and len(r[MSINV_SUBFORM]) > 0
                    for r in records
                )
                return records, has_lines
        except Exception:
            continue
    return [], False


def build_msinv_header_df(raw):
    df = pd.DataFrame(raw)
    if MSINV_SUBFORM in df.columns:
        df = df.drop(columns=[MSINV_SUBFORM])
    if "IVDATE" in df.columns and "CURDATE" in df.columns:
        df["IVDATE"] = df["IVDATE"].fillna(df["CURDATE"])
        df = df.drop(columns=["CURDATE"])
    df = df.rename(columns={k: v for k, v in MSINV_HEADER_MAP.items() if k in df.columns})
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Total Before Discount", "Price After Discount", "GST", "Grand Total")
    return df


def build_msinv_lines_df(raw):
    rows = []
    for inv in raw:
        lines = inv.get(MSINV_SUBFORM, [])
        if not lines:
            continue
        base = {
            "Invoice No.":   inv.get("IVNUM"),
            "Customer Name": inv.get("CDES"),
            "Date":          inv.get("IVDATE") or inv.get("CURDATE"),
            "Status":        inv.get("STATDES", ""),
            "Warehouse":     inv.get("WARHSNAME", ""),
        }
        for line in lines:
            row = {**base, **{v: line.get(k) for k, v in MSINV_LINE_MAP.items()}}
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = _parse_dates(df, "Date")
    df = _to_num(df, "Quantity", "Unit Price", "Discount %", "Total Price", "Line GST")
    return df


def build_msinv_merged_df(header_df, lines_df):
    if lines_df.empty:
        df = header_df.copy()
        df["Line Count"] = 0; df["Parts"] = ""; df["Lines Total"] = 0.0
        return df
    agg = (
        lines_df.groupby("Invoice No.")
        .agg(
            LC=("Part Description", "count"),
            LI=("Part Description", lambda x: ", ".join(x.dropna().astype(str).unique())),
            LT=("Total Price", "sum"),
        )
        .reset_index()
        .rename(columns={"LC": "Line Count", "LI": "Parts", "LT": "Lines Total"})
    )
    merged = header_df.merge(agg, on="Invoice No.", how="left")
    merged["Line Count"]  = merged["Line Count"].fillna(0).astype(int)
    merged["Parts"]       = merged["Parts"].fillna("")
    merged["Lines Total"] = pd.to_numeric(merged["Lines Total"], errors="coerce").fillna(0.0)
    return merged


def build_msinv_xml(inv: dict) -> str:
    """
    Build a Tally Sales Invoice XML (ISINVOICE=Yes, VCHTYPE=Sales)
    from a Priority CINVOICES (Multi Shipment Invoice) record.

    Key behaviour:
      - Distinct DOCCODE values from CINVOICEITEMS → one INVOICEDELNOTES.LIST
        block each in Dispatch Details (Delivery Note No(s.) field in Tally).
      - Each ALLINVENTORYENTRIES line carries TRACKINGNUMBER = its own DOCCODE
        so Tally links every item to the correct Shipment document.
      - Shipment date falls back to invoice date when not available on the line.

    Sign convention (Sales Invoice — stock OUT, customer owes us):
      ALLINVENTORYENTRIES  ISDEEMEDPOSITIVE=No,  AMOUNT positive  (stock debit out)
      ACCOUNTINGALLOCATIONS (Sales Account)  ISDEEMEDPOSITIVE=No,  AMOUNT positive
      Party LEDGERENTRIES  ISDEEMEDPOSITIVE=Yes, AMOUNT negative  (debtor — owes us)
      CGST/SGST/IGST       ISDEEMEDPOSITIVE=No,  AMOUNT positive  (output tax liability)
    """
    inv_no      = inv.get("Invoice No.")  or inv.get("IVNUM", "")
    raw_date    = inv.get("Date")         or inv.get("IVDATE", "") or inv.get("CURDATE", "")
    customer    = inv.get("Customer Name") or inv.get("CDES", "")
    warehouse   = inv.get("Warehouse")    or inv.get("WARHSNAME", "Main Location")
    # BRANCHNAME is the main-form field on CINVOICES that holds the branch/godown
    # code (e.g. R01-AN). Try all known Priority field name variants.
    branch      = str(
        inv.get("BRANCHNAME") or inv.get("Branch") or
        inv.get("BRANCH")     or inv.get("BRANCHDES") or
        inv.get("BRANCHCODE") or ""
    ).strip()
    header_wh   = branch or warehouse
    grand_tot   = float(inv.get("Grand Total")  or inv.get("TOTPRICE") or 0)
    gst_total   = float(inv.get("GST")           or inv.get("VAT")     or 0)
    party_gstin = str(inv.get("Customer GSTIN")  or inv.get("PARTYVAT") or "").strip()
    cust_state  = str(inv.get("Customer State")  or inv.get("STATENAME") or "").strip()
    order_ref   = str(inv.get("Order Number")    or inv.get("ORDNAME")   or "").strip()
    t_date      = _tally_date(str(raw_date))

    is_intrastate = _detect_intrastate(inv)
    # Override: if STATENAME (customer state) is explicitly present and matches
    # COMPANY_STATE, treat as intrastate regardless of TAXCODE. CINVOICES TAXCODE
    # is sometimes set to GST_OT by default even for local Maharashtra sales,
    # causing _detect_intrastate to return False. STATENAME is more reliable here.
    if cust_state and cust_state.strip().upper() == COMPANY_STATE.strip().upper():
        is_intrastate = True

    raw_lines = inv.get(MSINV_SUBFORM) or []

    # ── Collect all unique Shipment numbers + dates from subform lines ────────
    # CINVOICEITEMS.DOCCODE = the Shipment document number for each line
    # (e.g. SH26R01000007, SH26R01000008 …)
    # We gather them in insertion order (deduped) as (shipment_no, tally_date_str)
    # pairs so Tally can render each Shipment on its own line in Dispatch Details.
    _seen_sh = set()
    all_sh_pairs = []   # list of (shipment_no, tally_date_str)
    for _l in raw_lines:
        _s = str(_l.get("DOCNO") or _l.get("DOCCODE") or "").strip()
        if _s and _s not in _seen_sh:
            _seen_sh.add(_s)
            # Try line-level date fields; fall back to invoice date
            _raw_sh_date = (
                _l.get("UDATE") or _l.get("DOCDATE") or _l.get("CURDATE") or
                _l.get("IVDATE") or raw_date
            )
            _sh_date_str = _tally_date(str(_raw_sh_date)) if _raw_sh_date else t_date
            all_sh_pairs.append((_s, _sh_date_str))
    # Fallback: no DOCNO/DOCCODE on subform lines
    # → try header-level DOCNO/DNAME (single shipment direct conversion)
    # → last resort: use invoice number itself
    if not all_sh_pairs:
        _hdr_sh = str(inv.get("DOCNO") or inv.get("DNAME") or "").strip()
        if _hdr_sh and not _hdr_sh.startswith("SI"):
            all_sh_pairs = [(_hdr_sh, t_date)]
        else:
            all_sh_pairs = [(inv_no, t_date)]
    all_sh_nos     = [p[0] for p in all_sh_pairs]
    all_sh_nos_str = ", ".join(all_sh_nos)   # e.g. "SH26R01000007, SH26R01000008"

    # ── Build INVOICEDELNOTES.LIST blocks — one per Shipment ─────────────────
    # Confirmed pattern from live Tally Sales export XML (Sales_2.xml):
    #   <INVOICEDELNOTES.LIST>
    #     <BASICSHIPPINGDATE>YYYYMMDD</BASICSHIPPINGDATE>
    #     <BASICSHIPDELIVERYNOTE>SH26R01000007</BASICSHIPDELIVERYNOTE>
    #   </INVOICEDELNOTES.LIST>
    # Followed by a single empty INVOICEORDERLIST.LIST.
    # ── Build INVOICEDELNOTES.LIST + INVOICEORDERLIST.LIST blocks ───────────
    # Confirmed from live Tally Sales export XML (Sales_10.xml):
    #   INVOICEDELNOTES.LIST  → Delivery Note No(s)  (one block per Shipment)
    #   INVOICEORDERLIST.LIST → Order No(s)           (BASICPURCHASEORDERNO = SO ref)
    #
    # BASICPURCHASEORDERNO is the correct tag for "Order No(s)" — confirmed from
    # the reference export. BASICORDERREF / standalone voucher tags go to
    # "Other References" instead, so we never use those for the SO.
    _order_list_block = f"""
                        <INVOICEORDERLIST.LIST>
                            <BASICORDERDATE>{t_date}</BASICORDERDATE>
                            <BASICPURCHASEORDERNO>{order_ref}</BASICPURCHASEORDERNO>
                        </INVOICEORDERLIST.LIST>""" if order_ref else """
                        <INVOICEORDERLIST.LIST>      </INVOICEORDERLIST.LIST>"""
    invoicedelnotes_blocks = "".join(f"""
                        <INVOICEDELNOTES.LIST>
                            <BASICSHIPPINGDATE>{_dt}</BASICSHIPPINGDATE>
                            <BASICSHIPDELIVERYNOTE>{_sh}</BASICSHIPDELIVERYNOTE>
                        </INVOICEDELNOTES.LIST>""" for _sh, _dt in all_sh_pairs) + _order_list_block

    total_line_amt = sum(float(l.get("QPRICE") or l.get("Total Price") or 0) for l in raw_lines) or 1.0

    # ── GST rate resolution — RBS_TAXCODE on CINVOICEITEMS line ────────────────
    # RBS_TAXCODE (VAT Group) is present directly on every CINVOICEITEMS line.
    # This is the sole source for msinv — no PO lookup or global map needed.
    # _decode_mahi_taxrate handles the format: "001"→0% (exempt), "012"→12%, "028"→28%
    # Fallback: back-calculate from line VAT rupee amount, then proportional header.

    _MISSING = object()
    inv_entries = ""
    for line in raw_lines:
        pn   = str(line.get("PARTNAME") or line.get("Part Number", "")).strip()
        pd_  = str(line.get("PDES")     or line.get("Part Description", "")).strip()
        name = resolve_po_item_name(pn, pd_)
        if not name:
            continue
        try:
            qty  = float(line.get("TQUANT") or line.get("Quantity",   0))
            rate = float(line.get("PRICE")  or line.get("Unit Price",  0))
            amt  = float(line.get("QPRICE") or line.get("Total Price", 0))
        except Exception:
            qty = rate = amt = 0.0

        raw_unit = str(line.get("TUNITNAME") or line.get("Unit", "")).strip()
        unit = raw_unit if raw_unit else _resolve_unit(name)

        # BRANCHNAME is on the CINVOICES main form (header_wh), not on subform lines.
        # Fall back to header_wh (branch code e.g. R01-AN) when line has no warehouse.
        line_wh = str(line.get("WARHSNAME") or line.get("Warehouse") or "").strip() or header_wh

        # ── Cost-centre allocation block (mirrors PO / GRV logic) ────────────
        _ms_cc_alloc = f"""<CATEGORYALLOCATIONS.LIST>
                        <CATEGORY>Primary Cost Category</CATEGORY>
                        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                        <COSTCENTREALLOCATIONS.LIST>
                            <NAME>{branch}</NAME>
                            <AMOUNT>{amt:.2f}</AMOUNT>
                        </COSTCENTREALLOCATIONS.LIST>
                    </CATEGORYALLOCATIONS.LIST>""" if branch else ""

        # ── Per-line Shipment No. → TRACKINGNUMBER in BATCHALLOCATIONS ───────
        # Each CINVOICEITEMS row carries DOCCODE identifying which Shipment that
        # item came from.  Fall back to first shipment number if not available.
        line_shipment = str(line.get("DOCNO") or line.get("DOCCODE") or line.get("Shipment No.") or "").strip() or (all_sh_nos[0] if all_sh_nos else inv_no)

        # ── GST % from RBS_TAXCODE (VAT Group) ───────────────────────────────
        # Primary: RBS_TAXCODE on the CINVOICEITEMS line itself.
        # Fallback 1: back-calculate from VAT rupee amount on line.
        # Fallback 2: proportional from header GST total (last resort).
        total_gst_pct = 0.0
        _found = False

        # Primary — RBS_TAXCODE (VAT Group) directly on line
        _raw_rbs = line.get("RBS_TAXCODE")
        if _raw_rbs is not None:
            try:
                total_gst_pct = _decode_mahi_taxrate(_raw_rbs)
                _found = True
            except Exception:
                pass

        # Fallback 1 — back-calculate from line VAT rupee field
        if not _found:
            try:
                _lv = float(line.get("VAT") or line.get("Line GST") or 0)
            except Exception:
                _lv = 0.0
            if _lv > 0 and amt > 0:
                total_gst_pct = round(_lv / amt * 100, 2)
                _found = True

        # Fallback 2 — proportional from header GST total (absolute last resort)
        if not _found and gst_total > 0 and amt > 0:
            _lv = round(gst_total * (amt / total_line_amt), 2)
            total_gst_pct = round(_lv / amt * 100, 2) if _lv > 0 else 0.0

        cgst_pct = round(total_gst_pct / 2, 2)
        sgst_pct = round(total_gst_pct / 2, 2)
        igst_pct = total_gst_pct

        if total_gst_pct > 0:
            if is_intrastate:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>CGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{cgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>SGST/UTGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{sgst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
            else:
                rate_details = f"""
                <RATEDETAILS.LIST>
                    <GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD>
                    <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    <GSTRATE>{igst_pct}</GSTRATE>
                </RATEDETAILS.LIST>"""
        else:
            rate_details = ""

        # Sign convention for Sales Invoice (stock goes OUT):
        #   ISDEEMEDPOSITIVE=No, AMOUNT positive
        inv_entries += f"""
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{name}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <RATE>{rate:.2f}/{unit}</RATE>
                <AMOUNT>{amt:.2f}</AMOUNT>
                <VATASSBLVALUE>{amt:.2f}</VATASSBLVALUE>
                <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{line_wh}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <DESTINATIONGODOWNNAME>{line_wh}</DESTINATIONGODOWNNAME>
                    <TRACKINGNUMBER>{line_shipment}</TRACKINGNUMBER>
                    <ORDERNO>{order_ref}</ORDERNO>
                    <BASICBUYERORDERNO>{inv_no}</BASICBUYERORDERNO>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    <ACTUALQTY>{qty:.4f} {unit}</ACTUALQTY>
                    <BILLEDQTY>{qty:.4f} {unit}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
                <ACCOUNTINGALLOCATIONS.LIST>
                    <LEDGERNAME>{LEDGER_SALES}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <AMOUNT>{amt:.2f}</AMOUNT>
                    {_ms_cc_alloc}
                </ACCOUNTINGALLOCATIONS.LIST>{rate_details}
            </ALLINVENTORYENTRIES.LIST>"""

    # ── Slab-wise GST ledger entries (output tax liability — positive amounts) ─
    # Stamp RBS_TAXCODE as MAHI_TAXRATE on each line so _build_gst_groups can
    # compute slab-wise rupee amounts as QPRICE × rate/100.
    # Never copy rupee amounts from external sources — guarantees ledger totals
    # exactly match per-line RATEDETAILS computed above.
    enriched_lines_ms = []
    for _line in raw_lines:
        _enriched = dict(_line)
        _enriched.pop("CSTM_GST", None)
        _raw_rbs_e = _line.get("RBS_TAXCODE")
        if _raw_rbs_e is not None:
            try:
                _enriched["MAHI_TAXRATE"] = _decode_mahi_taxrate(_raw_rbs_e)
            except Exception:
                pass
        enriched_lines_ms.append(_enriched)

    gst_groups_msinv = _build_gst_groups(enriched_lines_ms, is_intrastate, gst_field="VAT", direction="output")
    if not gst_groups_msinv and gst_total > 0:
        if is_intrastate:
            _half = round(gst_total / 2, 2)
            gst_groups_msinv = {
                _gst_ledger_name("CGST", "9", "output"): _half,
                _gst_ledger_name("SGST", "9", "output"): round(gst_total - _half, 2),
            }
        else:
            gst_groups_msinv = {_gst_ledger_name("IGST", "18", "output"): gst_total}

    # Scale to match Priority's authoritative header GST total
    _computed = round(sum(gst_groups_msinv.values()), 2)
    if gst_total > 0 and _computed > 0 and abs(_computed - gst_total) > 1.0:
        _scale = gst_total / _computed
        gst_groups_msinv = {k: round(v * _scale, 2) for k, v in gst_groups_msinv.items()}
        _diff = round(gst_total - sum(gst_groups_msinv.values()), 2)
        if _diff != 0:
            _lk = max(gst_groups_msinv, key=gst_groups_msinv.get)
            gst_groups_msinv[_lk] = round(gst_groups_msinv[_lk] + _diff, 2)

    gst_entries = _gst_group_ledger_entries(
        gst_groups_msinv, is_intrastate, isdeemedpositive="No", sign=""
    )

    gstin_tag = f"<PARTYGSTIN>{party_gstin}</PARTYGSTIN>" if party_gstin else ""

    # ── No-line fallback: pure accounting Sales voucher ───────────────────────
    if not inv_entries.strip():
        taxable_base = round(grand_tot - gst_total, 2)
        no_line_sales = f"""
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{LEDGER_SALES}</LEDGERNAME>
                            <ISPARTYLEDGER>No</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                            <AMOUNT>{taxable_base:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>"""
        xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Accounting Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <NUMBERINGSTYLE>Manual</NUMBERINGSTYLE>
                        <REFERENCE>{inv_no}</REFERENCE>
                        <BASICBUYERORDERNO>{inv_no}</BASICBUYERORDERNO>
                        <BASICBUYERORDERDATE>{t_date}</BASICBUYERORDERDATE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>{COMPANY_STATE}</STATENAME>
                        <PLACEOFSUPPLY>{cust_state or COMPANY_STATE}</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{customer}</PARTYLEDGERNAME>
                        <PARTYNAME>{customer}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Multi Shipment Invoice from Priority ERP (no line items) | Shipment(s): {all_sh_nos_str}</NARRATION>
                        <ISINVOICE>No</ISINVOICE>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{customer}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                        </LEDGERENTRIES.LIST>{no_line_sales}{gst_entries}
                        {invoicedelnotes_blocks}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return xml.strip()

    # ── Normal path: inventory Sales Invoice ──────────────────────────────────
    xml = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">
                        <DATE>{t_date}</DATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        <VOUCHERNUMBER>{inv_no}</VOUCHERNUMBER>
                        <NUMBERINGSTYLE>Manual</NUMBERINGSTYLE>
                        <REFERENCE>{inv_no}</REFERENCE>
                        <BASICBUYERORDERNO>{order_ref or inv_no}</BASICBUYERORDERNO>
                        <BASICBUYERORDERDATE>{t_date}</BASICBUYERORDERDATE>
                        <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
                        <STATENAME>{COMPANY_STATE}</STATENAME>
                        <PLACEOFSUPPLY>{cust_state or COMPANY_STATE}</PLACEOFSUPPLY>
                        <PARTYLEDGERNAME>{customer}</PARTYLEDGERNAME>
                        <PARTYNAME>{customer}</PARTYNAME>
                        {gstin_tag}
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        <NARRATION>Final Multi Shipment Invoice from Priority ERP | Shipment(s): {all_sh_nos_str}</NARRATION>
                        <ISINVOICE>Yes</ISINVOICE>
                        <DIFFACTUALQTY>Yes</DIFFACTUALQTY>
                        {f'<ISCOSTCENTRE>Yes</ISCOSTCENTRE>' if branch else ''}
                        {f'<COSTCENTRENAME>{branch}</COSTCENTRENAME>' if branch else ''}
                        {inv_entries}
                        <LEDGERENTRIES.LIST>
                            <LEDGERNAME>{customer}</LEDGERNAME>
                            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                            <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                            <BILLALLOCATIONS.LIST>
                                <NAME>{inv_no}</NAME>
                                <BILLTYPE>New Ref</BILLTYPE>
                                <AMOUNT>-{grand_tot:.2f}</AMOUNT>
                            </BILLALLOCATIONS.LIST>
                        </LEDGERENTRIES.LIST>{gst_entries}
                        {invoicedelnotes_blocks}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
    return xml.strip()


def run_msinv_push(invoices: list, dry_run: bool, source: str) -> list:
    """Push Final Multi Shipment Invoices to Tally as Sales Invoice vouchers (ISINVOICE=Yes)."""
    results = []; prog = st.progress(0); status_ph = st.empty(); total = len(invoices)
    if not dry_run:
        status_ph.info("⚙ Step 1/2 — Creating missing customer ledgers & stock items in Tally…")
        for rec in invoices:
            c = rec.get("Customer Name") or rec.get("CDES", "")
            if c:
                ensure_vendor_ledger(c, "Sundry Debtors")
            _is_intra = _detect_intrastate(rec)
            for line in (rec.get(MSINV_SUBFORM) or []):
                item_name = resolve_po_item_name(line.get("PARTNAME", ""), line.get("PDES", ""))
                if item_name:
                    _rate = 0.0
                    _raw_mr = line.get("MAHI_TAXRATE")
                    if _raw_mr is not None:
                        try:
                            _rate = _decode_mahi_taxrate(_raw_mr)
                        except Exception:
                            pass
                    ensure_stock_item(item_name, "", gst_rate=_rate, is_intrastate=_is_intra)
        status_ph.info("⚙ Step 2/2 — Pushing Sales Invoice vouchers to Tally…")
    for i, rec in enumerate(invoices):
        inv_no   = rec.get("Invoice No.") or rec.get("IVNUM", "?")
        status   = rec.get("Status")      or rec.get("STATDES", "")
        customer = rec.get("Customer Name") or rec.get("CDES", "")
        amount   = rec.get("Grand Total")  or rec.get("TOTPRICE") or 0
        status_ph.markdown(f"**[{source}]** Pushing `{inv_no}` ({i+1}/{total})…")
        xml = build_msinv_xml(rec)
        if dry_run:
            results.append({
                "Source": source, "Invoice No": inv_no, "Status": status,
                "Customer": customer, "Amount": fmt_inr(amount),
                "Tally Type": "Sales (Invoice)",
                "Result": "🧪 Dry run — XML built, not pushed",
                "XML": xml, "Timestamp": datetime.now().strftime("%H:%M:%S"),
            })
        else:
            ok, msg, tally_raw = push_to_tally(xml)
            results.append({
                "Source": source, "Invoice No": inv_no, "Status": status,
                "Customer": customer, "Amount": fmt_inr(amount),
                "Tally Type": "Sales (Invoice)",
                "Result": f"{'✅' if ok else '❌'} {msg}",
                "XML": xml, "Tally Response": tally_raw,
                "Timestamp": datetime.now().strftime("%H:%M:%S"),
            })
            time.sleep(0.25)
        prog.progress((i + 1) / total)
    prog.empty(); status_ph.empty()
    return results



#  APP HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="app-header">
    <div class="app-logo">🔗</div>
    <div>
        <p class="app-title">Priority → Tally Middleware</p>
        <p class="app-subtitle">Active Module: <b>{active_module}</b> · Terminal: {TALLY_COMPANY}</p>
    </div>
    <div class="app-badge">Live · No Database</div>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 1: PURCHASE ORDERS
# ═══════════════════════════════════════════════════════════════════════════════
if active_module == "Purchase Orders Module":

    with st.spinner("Fetching Purchase Orders from Priority ERP & Tally Day Book…"):
        tally_po_nos = query_daybook_by_type("Purchase Order")
        tally_po_nos = tally_po_nos | st.session_state.get("po_tally_nos_override", set())
        try:
            raw_data, has_lines = fetch_orders()
            header_df = build_header_df(raw_data)
            lines_df  = build_lines_df(raw_data)
            merged_df = build_merged_df(header_df, lines_df)
            fetch_error = None
        except Exception as e:
            fetch_error = str(e); raw_data = []; header_df = pd.DataFrame()
            lines_df = pd.DataFrame(); merged_df = pd.DataFrame(); has_lines = False

    if fetch_error:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error: {fetch_error}</div>', unsafe_allow_html=True)
        st.stop()

    if not header_df.empty:
        po_total  = len(header_df)
        po_auth   = int(header_df["Status"].eq("Authorised").sum()) if "Status" in header_df.columns else 0
        po_final  = int(header_df["Status"].isin(["Final", "Completed"]).sum()) if "Status" in header_df.columns else 0
        po_closed = int(header_df["Status"].eq("Closed").sum()) if "Status" in header_df.columns else 0
        total_amt = header_df["Total Cost (INR)"].sum() if "Total Cost (INR)" in header_df.columns else 0
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Orders</div><div class="kpi-count">{po_total}</div><div class="kpi-amount">{fmt_inr(total_amt)} total</div></div>
            <div class="kpi kpi-auth"><div class="kpi-label">🔷 Authorised</div><div class="kpi-count">{po_auth}</div><div class="kpi-amount">Ready to push</div></div>
            <div class="kpi kpi-final"><div class="kpi-label">✨ Final / Completed</div><div class="kpi-count">{po_final}</div><div class="kpi-amount">Ready to push</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">🚫 Closed</div><div class="kpi-count">{po_closed}</div><div class="kpi-amount">Not pushed</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_po_nos)}</div><div class="kpi-amount">Vouchers in Day Book</div></div>
        </div>""", unsafe_allow_html=True)

    po_tab1, po_tab2, po_tab3 = st.tabs([
        f"📋 Purchase Orders ({len(merged_df)})",
        "🔍 Integrity Validation Grid",
        "🔁 Tally Sync",
    ])

    with po_tab1:
        st.markdown('<p class="sec">Purchase Orders</p>', unsafe_allow_html=True)
        # ── Row 1: Status / Vendor / Search ──
        po_f1, po_f2, po_f3 = st.columns([2, 2, 4])
        with po_f1:
            po_sel_status = st.selectbox("Status Filter:", ["Authorised Only", "All Eligible", "Final/Completed Only", "All"])
        with po_f2:
            _po_vends = ["All"] + sorted(header_df["Vendor Name"].dropna().unique().tolist()) if "Vendor Name" in header_df.columns else ["All"]
            po_sel_vend = st.selectbox("Vendor:", _po_vends)
        with po_f3:
            po_search_str = st.text_input("Search Order / Vendor:", placeholder="e.g. PO26R010")

        # ── Row 2: Date filter ──
        po_d1, po_d2, po_d3 = st.columns([2, 2, 4])
        with po_d1:
            _po_today = datetime.today().date()
            po_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="po_date_preset")
        po_date_from = po_date_to = None
        if po_date_preset == "Today":
            po_date_from = po_date_to = _po_today
        elif po_date_preset == "Yesterday":
            from datetime import timedelta
            po_date_from = po_date_to = _po_today - timedelta(days=1)
        elif po_date_preset == "Last 7 Days":
            from datetime import timedelta
            po_date_from = _po_today - timedelta(days=6); po_date_to = _po_today
        elif po_date_preset == "This Month":
            po_date_from = _po_today.replace(day=1); po_date_to = _po_today
        elif po_date_preset == "Custom Range":
            with po_d2:
                po_date_from = st.date_input("From:", value=_po_today.replace(day=1), key="po_date_from")
            with po_d3:
                po_date_to   = st.date_input("To:", value=_po_today, key="po_date_to")
        else:
            with po_d2:
                st.caption("Showing **all dates**")

        po_filt_df = merged_df.copy() if not merged_df.empty else pd.DataFrame()
        if "Status" in po_filt_df.columns:
            if po_sel_status == "Authorised Only":        po_filt_df = po_filt_df[po_filt_df["Status"] == "Authorised"]
            elif po_sel_status == "All Eligible":         po_filt_df = po_filt_df[po_filt_df["Status"].isin(ELIGIBLE_STATUSES)]
            elif po_sel_status == "Final/Completed Only": po_filt_df = po_filt_df[po_filt_df["Status"].isin(["Final", "Completed"])]
        if po_sel_vend != "All" and "Vendor Name" in po_filt_df.columns:
            po_filt_df = po_filt_df[po_filt_df["Vendor Name"] == po_sel_vend]
        if po_search_str.strip() and "Order" in po_filt_df.columns:
            po_filt_df = po_filt_df[po_filt_df["Order"].astype(str).str.contains(po_search_str.strip(), case=False, na=False)]
        # ── Apply date filter ──
        if (po_date_from or po_date_to) and "Date" in po_filt_df.columns:
            _po_dates = pd.to_datetime(po_filt_df["Date"], format="%d %b %Y", errors="coerce").dt.date
            _po_valid = _po_dates.apply(lambda d: d is not None and not (isinstance(d, float)))
            if po_date_from: po_filt_df = po_filt_df[_po_valid & (_po_dates.apply(lambda d: d is not None and d >= po_date_from))]
            if po_date_to:   po_filt_df = po_filt_df[_po_valid & (_po_dates.apply(lambda d: d is not None and d <= po_date_to))]

        # ── Compute filtered order numbers → pipeline for Tab 2 & 3 ──
        _po_tab1_order_nos = set(po_filt_df["Order"].astype(str).tolist()) if not po_filt_df.empty and "Order" in po_filt_df.columns else set()
        # Filtered raw records (for integrity check & push engine)
        po_pipeline_raw = [r for r in raw_data if str(r.get("ORDNAME", "")).strip() in _po_tab1_order_nos]
        st.session_state["po_pipeline_raw"] = po_pipeline_raw

        if not po_filt_df.empty:
            po_filt_df = po_filt_df.copy()
            po_filt_df["Tally Match"] = po_filt_df["Order"].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_po_nos else "🆕 Safe to Push"
            )
            po_cols = ["Status", "Tally Match", "Order", "Date", "Vendor Number", "Vendor Name",
                       "Total Cost (INR)", "Warehouse", "Line Count"]
            st.dataframe(fmt_cur(po_filt_df[[c for c in po_cols if c in po_filt_df.columns]], "Total Cost (INR)"),
                         use_container_width=True, height=480, hide_index=True)
            st.caption(f"ℹ️ {len(po_filt_df)} order(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            with st.expander("🔬 Raw API Field Diagnostic — check if BRANCHNAME is coming from Priority", expanded=False):
                if raw_data:
                    _po_sample = {k: v for k, v in raw_data[0].items() if k != SUBFORM_NAV}
                    st.markdown("**All header fields returned by Priority for the first Purchase Order:**")
                    st.json(_po_sample)
                    _po_branch_keys = [k for k in _po_sample if "BRANCH" in k.upper()]
                    if _po_branch_keys:
                        st.success(f"✅ Branch field(s) found: {_po_branch_keys} → values: {[_po_sample[k] for k in _po_branch_keys]}")
                    else:
                        st.error("❌ No BRANCH* field in Priority response for PORDERS — check if BRANCHNAME exists on this form in your Priority setup.")
                else:
                    st.info("No raw data available.")
        else:
            st.session_state["po_pipeline_raw"] = []
            st.markdown('<div class="alert alert-warn">⚠ No orders match the current filters.</div>', unsafe_allow_html=True)

    with po_tab2:
        st.markdown('<p class="sec">Integrity Validation — Priority vs Tally</p>', unsafe_allow_html=True)
        _po_pipe = st.session_state.get("po_pipeline_raw", None)
        if _po_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Purchase Orders</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _po_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No orders match the current filters in the Purchase Orders tab.</div>', unsafe_allow_html=True)
        else:
            po_matrix = []
            _po_safe_nos = set()
            for rec in _po_pipe:
                ord_ref  = rec.get("ORDNAME", "")
                stat_ref = str(rec.get("STATDES") or "").strip()
                vendor   = str(rec.get("CDES") or "").strip()
                raw_dt   = rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("MAINDISPRICE") or 0)
                warehouse = str(rec.get("WARHSNAME") or "").strip()
                in_tally = ord_ref in tally_po_nos
                if in_tally:
                    verdict = "❌ Duplicate — Already in Tally"
                elif stat_ref in ELIGIBLE_STATUSES:
                    verdict = f"✅ Safe to Push ({stat_ref})"
                    _po_safe_nos.add(ord_ref)
                else:
                    verdict = f"🚫 Not Eligible ({stat_ref})"
                po_matrix.append({
                    "Verdict":      verdict,
                    "Order":        ord_ref,
                    "Date":         date_str,
                    "Vendor":       vendor,
                    "Amount":       amount,
                    "Warehouse":    warehouse,
                    "Status":       stat_ref,
                    "Tally Match":  "Found" if in_tally else "Not Found",
                })
            st.session_state["po_safe_order_nos"] = _po_safe_nos
            st.dataframe(pd.DataFrame(po_matrix), use_container_width=True, hide_index=True)
            safe_n = len(_po_safe_nos)
            dup_n  = sum(1 for r in po_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in po_matrix if "Not Eligible" in r["Verdict"])
            st.caption(f"✅ {safe_n} safe to push · ❌ {dup_n} duplicate(s) · 🚫 {skip_n} ineligible")

    with po_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Purchase Orders</p>', unsafe_allow_html=True)

        # Pull pipeline from session state: only orders that cleared integrity in Tab 2
        _po_pipe3      = st.session_state.get("po_pipeline_raw", raw_data)
        _po_safe_nos3  = st.session_state.get("po_safe_order_nos", None)

        if _po_safe_nos3 is None:
            # Tab 2 not yet visited — compute on the fly
            _po_safe_nos3 = {r.get("ORDNAME", "") for r in _po_pipe3
                             if str(r.get("STATDES") or "").strip() in ELIGIBLE_STATUSES
                             and r.get("ORDNAME", "") not in tally_po_nos}

        po_sync_target = st.radio("Queue to process:",
                                  ["Authorised Orders", "Final / Completed Orders"], horizontal=True)
        target_status = "Authorised" if po_sync_target == "Authorised Orders" else "Final"

        # Filter pool: must be in safe set AND match the radio choice
        po_pool = [r for r in _po_pipe3
                   if r.get("ORDNAME", "") in _po_safe_nos3 and (
                       str(r.get("STATDES") or "").strip() == target_status or
                       (target_status == "Final" and str(r.get("STATDES") or "").strip() == "Completed")
                   )]

        # ── Apply same date filter as Tab 1 ──
        if po_date_from or po_date_to:
            def _po_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except: return None
            po_pool = [r for r in po_pool if (lambda d: d is not None and
                       (not po_date_from or d >= po_date_from) and
                       (not po_date_to   or d <= po_date_to))(_po_rec_date(r))]
            _po_date_label = (f"{po_date_from}" if po_date_from == po_date_to
                              else f"{po_date_from} → {po_date_to}" if po_date_from and po_date_to
                              else f"from {po_date_from}" if po_date_from else f"until {po_date_to}")
            st.markdown(f'<div class="alert alert-info">📅 Date filter active: <b>{po_date_preset}</b> ({_po_date_label})</div>', unsafe_allow_html=True)

        st.markdown('<div class="alert alert-info">ℹ️ Only orders that passed the <b>Integrity Validation</b> step are shown here. Orders already in Tally, or with ineligible statuses, have been excluded.</div>', unsafe_allow_html=True)

        po_hide_existing = st.checkbox("Hide orders already in Tally", value=True, key="po_hide_ex")
        if po_hide_existing:
            po_pool = [r for r in po_pool if str(r.get("ORDNAME", "")).strip() not in tally_po_nos]

        st.caption(f"**{len(po_pool)}** order(s) in queue.")
        if not po_pool:
            st.info("No outstanding orders to process in this queue.")
        else:
            selected_po = []
            for rec in po_pool:
                ord_id   = rec.get("ORDNAME", "?")
                vend_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("MAINDISPRICE") or 0)
                is_dup   = ord_id in tally_po_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(f"**{ord_id}** — {vend_lbl} — {val_lbl}{warn}",
                               value=not is_dup, key=f"po_chk_{ord_id}"):
                    selected_po.append(rec)
            st.markdown("---")
            po_dry = st.checkbox("Dry run (preview only)", value=False, key="po_dry")
            if st.button(f"{'🧪 Dry Run' if po_dry else '🚀 Push'} {len(selected_po)} PO(s) to Tally",
                         key="po_push_btn"):
                if not selected_po:
                    st.warning("No orders selected.")
                else:
                    render_push_results(run_po_push(selected_po, po_dry, f"PO-{target_status}"), po_dry)

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 2: SALES ORDERS
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Sales Orders Module":

    with st.spinner("Fetching Sales Orders from Priority ERP & Tally Day Book…"):
        tally_so_nos = query_daybook_by_type("Sales Order")
        try:
            so_raw, so_has_lines = fetch_sales_orders()
            so_header_df = build_so_header_df(so_raw) if so_raw else pd.DataFrame()
            so_lines_df  = build_so_lines_df(so_raw)  if so_raw else pd.DataFrame()
            so_merged_df = build_so_merged_df(so_header_df, so_lines_df) if not so_header_df.empty else pd.DataFrame()
            so_fetch_err = None
        except Exception as e:
            so_fetch_err = str(e); so_raw = []; so_header_df = pd.DataFrame()
            so_lines_df = pd.DataFrame(); so_merged_df = pd.DataFrame(); so_has_lines = False

    if so_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error: {so_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if not so_header_df.empty:
        so_total     = len(so_header_df)
        so_confirmed = int(so_header_df["Status"].eq("Confirmed").sum()) if "Status" in so_header_df.columns else 0
        so_final_s   = int(so_header_df["Status"].eq("Final").sum()) if "Status" in so_header_df.columns else 0
        so_pending   = int(so_header_df["Status"].isin(["Pending Auth", "Draft"]).sum()) if "Status" in so_header_df.columns else 0
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Sales Orders</div><div class="kpi-count">{so_total}</div><div class="kpi-amount">All pipeline items</div></div>
            <div class="kpi kpi-confirmed"><div class="kpi-label">🔷 Confirmed</div><div class="kpi-count">{so_confirmed}</div><div class="kpi-amount">Ready to push</div></div>
            <div class="kpi kpi-final"><div class="kpi-label">✨ Final</div><div class="kpi-count">{so_final_s}</div><div class="kpi-amount">Ready to push</div></div>
            <div class="kpi kpi-auth"><div class="kpi-label">⏳ Pending / Draft</div><div class="kpi-count">{so_pending}</div><div class="kpi-amount">Awaiting approval</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_so_nos)}</div><div class="kpi-amount">Vouchers in Day Book</div></div>
        </div>""", unsafe_allow_html=True)

    so_tab1, so_tab2, so_tab3 = st.tabs([
        f"🛒 Sales Orders ({len(so_merged_df)})",
        "🔍 Integrity Validation Grid",
        "🔁 Tally Sync",
    ])

    with so_tab1:
        st.markdown('<p class="sec">Sales Orders</p>', unsafe_allow_html=True)
        # ── Row 1: Status / Customer / Search ──
        so_f1, so_f2, so_f3 = st.columns([2, 2, 4])
        with so_f1:
            so_sel_status = st.selectbox("Status Filter:", ["Confirmed Only", "All Eligible", "Final Only", "All"])
        with so_f2:
            _so_custs = ["All"] + sorted(so_header_df["Cust. Name"].dropna().unique().tolist()) if "Cust. Name" in so_header_df.columns else ["All"]
            so_sel_cust = st.selectbox("Customer:", _so_custs)
        with so_f3:
            so_search_str = st.text_input("Search Order / Customer:", placeholder="e.g. SO260001")

        # ── Row 2: Date filter ──
        so_d1, so_d2, so_d3 = st.columns([2, 2, 4])
        with so_d1:
            _so_today = datetime.today().date()
            so_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="so_date_preset")
        so_date_from = so_date_to = None
        if so_date_preset == "Today":
            so_date_from = so_date_to = _so_today
        elif so_date_preset == "Yesterday":
            from datetime import timedelta
            so_date_from = so_date_to = _so_today - timedelta(days=1)
        elif so_date_preset == "Last 7 Days":
            from datetime import timedelta
            so_date_from = _so_today - timedelta(days=6); so_date_to = _so_today
        elif so_date_preset == "This Month":
            so_date_from = _so_today.replace(day=1); so_date_to = _so_today
        elif so_date_preset == "Custom Range":
            with so_d2:
                so_date_from = st.date_input("From:", value=_so_today.replace(day=1), key="so_date_from")
            with so_d3:
                so_date_to   = st.date_input("To:", value=_so_today, key="so_date_to")
        else:
            with so_d2:
                st.caption("Showing **all dates**")

        so_filt_df = so_merged_df.copy() if not so_merged_df.empty else pd.DataFrame()
        if "Status" in so_filt_df.columns:
            if so_sel_status == "Confirmed Only":   so_filt_df = so_filt_df[so_filt_df["Status"] == "Confirmed"]
            elif so_sel_status == "All Eligible":   so_filt_df = so_filt_df[so_filt_df["Status"].isin(SO_PUSH_STATUSES)]
            elif so_sel_status == "Final Only":     so_filt_df = so_filt_df[so_filt_df["Status"] == "Final"]
        if so_sel_cust != "All" and "Cust. Name" in so_filt_df.columns:
            so_filt_df = so_filt_df[so_filt_df["Cust. Name"] == so_sel_cust]
        if so_search_str.strip() and "Order No." in so_filt_df.columns:
            so_filt_df = so_filt_df[so_filt_df["Order No."].astype(str).str.contains(so_search_str.strip(), case=False, na=False)]
        # ── Apply date filter ──
        if (so_date_from or so_date_to) and "DATE" in so_filt_df.columns:
            _so_dates = pd.to_datetime(so_filt_df["DATE"], format="%d %b %Y", errors="coerce").dt.date
            if so_date_from: so_filt_df = so_filt_df[_so_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= so_date_from)]
            if so_date_to:   so_filt_df = so_filt_df[_so_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= so_date_to)]

        # ── Compute filtered order numbers → pipeline for Tab 2 & 3 ──
        _so_tab1_order_nos = set(so_filt_df["Order No."].astype(str).tolist()) if not so_filt_df.empty and "Order No." in so_filt_df.columns else set()
        so_pipeline_raw = [r for r in so_raw if str(r.get("ORDNAME", "")).strip() in _so_tab1_order_nos]
        st.session_state["so_pipeline_raw"] = so_pipeline_raw

        if not so_filt_df.empty:
            so_filt_df = so_filt_df.copy()
            so_filt_df["Tally Match"] = so_filt_df["Order No."].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_so_nos else "🆕 Safe to Push"
            )
            so_cols = ["Status", "Tally Match", "Order No.", "DATE", "Customer No.", "Cust. Name",
                       "Final Price", "Line Count"]
            st.dataframe(fmt_cur(so_filt_df[[c for c in so_cols if c in so_filt_df.columns]], "Final Price"),
                         use_container_width=True, height=480, hide_index=True)
            st.caption(f"ℹ️ {len(so_filt_df)} order(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            # ── Raw API field diagnostic (helps debug missing fields like BRANCHNAME) ──
            with st.expander("🔬 Raw API Field Diagnostic — first record from Priority", expanded=False):
                if so_raw:
                    _sample = {k: v for k, v in so_raw[0].items() if k != SO_SUBFORM_NAV}
                    st.markdown("**All header fields returned by Priority for the first Sales Order:**")
                    st.json(_sample)
                    _branch_keys = [k for k in _sample if "BRANCH" in k.upper()]
                    if _branch_keys:
                        st.success(f"✅ Branch-related field(s) found: {_branch_keys} → values: {[_sample[k] for k in _branch_keys]}")
                    else:
                        st.error("❌ No BRANCH* field found in the Priority response. Priority may not populate BRANCHNAME on ORDERS, or the field has a different name.")
                else:
                    st.info("No raw data available yet.")
        else:
            st.session_state["so_pipeline_raw"] = []
            st.markdown('<div class="alert alert-warn">⚠ No orders match the current filters.</div>', unsafe_allow_html=True)

    with so_tab2:
        st.markdown('<p class="sec">Integrity Validation — Priority vs Tally</p>', unsafe_allow_html=True)
        _so_pipe = st.session_state.get("so_pipeline_raw", None)
        if _so_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Sales Orders</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _so_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No orders match the current filters in the Sales Orders tab.</div>', unsafe_allow_html=True)
        else:
            so_matrix = []
            _so_safe_nos = set()
            for rec in _so_pipe:
                ord_ref  = rec.get("ORDNAME", "")
                stat_ref = str(rec.get("ORDSTATUSDES") or rec.get("STATDES") or "").strip()
                customer = str(rec.get("CDES") or "").strip()
                raw_dt   = rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("TOTPRICE") or 0)
                in_tally = ord_ref in tally_so_nos
                if in_tally:
                    verdict = "❌ Duplicate — Already in Tally"
                elif stat_ref in SO_PUSH_STATUSES:
                    verdict = f"✅ Safe to Push ({stat_ref})"
                    _so_safe_nos.add(ord_ref)
                else:
                    verdict = f"🚫 Not Eligible ({stat_ref})"
                so_matrix.append({
                    "Verdict":     verdict,
                    "Order":       ord_ref,
                    "Date":        date_str,
                    "Customer":    customer,
                    "Amount":      amount,
                    "Status":      stat_ref,
                    "Tally Match": "Found" if in_tally else "Not Found",
                })
            st.session_state["so_safe_order_nos"] = _so_safe_nos
            st.dataframe(pd.DataFrame(so_matrix), use_container_width=True, hide_index=True)
            safe_n = len(_so_safe_nos)
            dup_n  = sum(1 for r in so_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in so_matrix if "Not Eligible" in r["Verdict"])
            st.caption(f"✅ {safe_n} safe to push · ❌ {dup_n} duplicate(s) · 🚫 {skip_n} ineligible")

    with so_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Sales Orders</p>', unsafe_allow_html=True)

        # Pull pipeline from session state: only orders that cleared integrity in Tab 2
        _so_pipe3     = st.session_state.get("so_pipeline_raw", so_raw)
        _so_safe_nos3 = st.session_state.get("so_safe_order_nos", None)

        if _so_safe_nos3 is None:
            # Tab 2 not yet visited — compute on the fly
            _so_safe_nos3 = {r.get("ORDNAME", "") for r in _so_pipe3
                             if str(r.get("ORDSTATUSDES") or r.get("STATDES") or "").strip() in SO_PUSH_STATUSES
                             and r.get("ORDNAME", "") not in tally_so_nos}

        so_sync_target = st.radio("Queue to process:",
                                  ["Confirmed Orders", "Final Orders"], horizontal=True)
        so_target_status = "Confirmed" if so_sync_target == "Confirmed Orders" else "Final"

        # Filter pool: must be in safe set AND match the radio choice
        so_pool = [r for r in _so_pipe3
                   if r.get("ORDNAME", "") in _so_safe_nos3 and
                   str(r.get("ORDSTATUSDES") or r.get("STATDES") or "").strip() == so_target_status]

        # ── Apply same date filter as Tab 1 ──
        if so_date_from or so_date_to:
            def _so_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except: return None
            so_pool = [r for r in so_pool if (lambda d: d is not None and
                       (not so_date_from or d >= so_date_from) and
                       (not so_date_to   or d <= so_date_to))(_so_rec_date(r))]
            _so_date_label = (f"{so_date_from}" if so_date_from == so_date_to
                              else f"{so_date_from} → {so_date_to}" if so_date_from and so_date_to
                              else f"from {so_date_from}" if so_date_from else f"until {so_date_to}")
            st.markdown(f'<div class="alert alert-info">📅 Date filter active: <b>{so_date_preset}</b> ({_so_date_label})</div>', unsafe_allow_html=True)

        st.markdown('<div class="alert alert-info">ℹ️ Only orders that passed the <b>Integrity Validation</b> step are shown here. Orders already in Tally, or with ineligible statuses, have been excluded.</div>', unsafe_allow_html=True)

        so_hide_existing = st.checkbox("Hide orders already in Tally", value=True, key="so_hide_ex")
        if so_hide_existing:
            so_pool = [r for r in so_pool if str(r.get("ORDNAME", "")).strip() not in tally_so_nos]

        st.caption(f"**{len(so_pool)}** order(s) in queue.")
        if not so_pool:
            st.info("No outstanding orders to process in this queue.")
        else:
            selected_so = []
            for rec in so_pool:
                ord_id   = rec.get("ORDNAME", "?")
                cust_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("TOTPRICE") or 0)
                is_dup   = ord_id in tally_so_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(f"**{ord_id}** — {cust_lbl} — {val_lbl}{warn}",
                               value=not is_dup, key=f"so_chk_{ord_id}"):
                    selected_so.append(rec)
            st.markdown("---")
            so_dry = st.checkbox("Dry run (preview only)", value=False, key="so_dry")
            if st.button(f"{'🧪 Dry Run' if so_dry else '🚀 Push'} {len(selected_so)} SO(s) to Tally",
                         key="so_push_btn"):
                if not selected_so:
                    st.warning("No orders selected.")
                else:
                    render_push_results(run_so_push(selected_so, so_dry, f"SO-{so_target_status}"), so_dry)

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE 3: SALES INVOICES  (AINVOICES — Final status → Tally Sales Invoice)
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Sales Invoices Module":

    with st.spinner("Fetching Final Sales Invoices from Priority ERP (AINVOICES)…"):
        tally_sinv_nos = query_daybook_by_type("Sales")
        try:
            sinv_raw, sinv_has_lines = fetch_sales_invoices()
            # Filter to Final status only (display all but push-gate is Final)
            sinv_header_df = build_sinv_header_df(sinv_raw) if sinv_raw else pd.DataFrame()
            sinv_lines_df  = build_sinv_lines_df(sinv_raw)  if sinv_raw else pd.DataFrame()
            sinv_merged_df = build_sinv_merged_df(sinv_header_df, sinv_lines_df) if not sinv_header_df.empty else pd.DataFrame()
            sinv_fetch_err = None
        except Exception as e:
            sinv_fetch_err = str(e); sinv_raw = []; sinv_header_df = pd.DataFrame()
            sinv_lines_df = pd.DataFrame(); sinv_merged_df = pd.DataFrame(); sinv_has_lines = False

    if sinv_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error (AINVOICES): {sinv_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if not sinv_header_df.empty:
        sinv_total  = len(sinv_header_df)
        sinv_final  = int(sinv_header_df["Status"].eq(SINV_PUSH_STATUS).sum()) if "Status" in sinv_header_df.columns else 0
        sinv_other  = sinv_total - sinv_final
        sinv_amt    = sinv_header_df["Grand Total"].sum() if "Grand Total" in sinv_header_df.columns else 0
        sinv_amt_f  = sinv_header_df[sinv_header_df.get("Status", pd.Series()) == SINV_PUSH_STATUS]["Grand Total"].sum() if "Grand Total" in sinv_header_df.columns and "Status" in sinv_header_df.columns else 0
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Invoices</div><div class="kpi-count">{sinv_total}</div><div class="kpi-amount">{fmt_inr(sinv_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">✅ Final — Ready to Push</div><div class="kpi-count">{sinv_final}</div><div class="kpi-amount">{fmt_inr(sinv_amt_f)}</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">⏳ Other Statuses</div><div class="kpi-count">{sinv_other}</div><div class="kpi-amount">Not pushed</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_sinv_nos)}</div><div class="kpi-amount">Sales vouchers in Tally</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span>🟡 <b style="color:#e3b341">Final</b> → Tally <b>Sales Invoice</b> (ISINVOICE=Yes)</span>
            <span>⚙ Header: AINVOICES &nbsp;|&nbsp; Lines: AINVOICEITEMS</span>
            <span>💰 Party ledger: Sundry Debtors &nbsp;|&nbsp; Sales ledger: Sales Account</span>
        </div>""", unsafe_allow_html=True)

    sinv_tab1, sinv_tab2, sinv_tab3 = st.tabs([
        f"🧾 Sales Invoices ({len(sinv_merged_df) if not sinv_merged_df.empty else 0})",
        "🔍 Integrity Validation Grid",
        f"🚀 Tally Sync ({sinv_final if not sinv_header_df.empty else 0} Final)",
    ])

    # ── TAB 1: Invoice list ───────────────────────────────────────────────────
    with sinv_tab1:
        st.markdown('<p class="sec">Sales Invoices — AINVOICES</p>', unsafe_allow_html=True)

        si_f1, si_f2, si_f3 = st.columns([2, 2, 4])
        with si_f1:
            _sinv_statuses = ["All"] + (sorted(sinv_header_df["Status"].dropna().unique().tolist())
                                        if "Status" in sinv_header_df.columns else [])
            si_sel_status = st.selectbox("Status:", _sinv_statuses, key="si_status")
        with si_f2:
            _sinv_custs = ["All"] + (sorted(sinv_header_df["Cust. Name"].dropna().unique().tolist())
                                     if "Cust. Name" in sinv_header_df.columns else [])
            si_sel_cust = st.selectbox("Customer:", _sinv_custs, key="si_cust")
        with si_f3:
            si_search = st.text_input("Search Invoice No. / Customer:", placeholder="e.g. IN264R01", key="si_search")

        # Date filter
        si_d1, si_d2, si_d3 = st.columns([2, 2, 4])
        with si_d1:
            _si_today = datetime.today().date()
            si_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="si_date")
        si_date_from = si_date_to = None
        if si_date_preset == "Today":
            si_date_from = si_date_to = _si_today
        elif si_date_preset == "Yesterday":
            from datetime import timedelta
            si_date_from = si_date_to = _si_today - timedelta(days=1)
        elif si_date_preset == "Last 7 Days":
            from datetime import timedelta
            si_date_from = _si_today - timedelta(days=6); si_date_to = _si_today
        elif si_date_preset == "This Month":
            si_date_from = _si_today.replace(day=1); si_date_to = _si_today
        elif si_date_preset == "Custom Range":
            with si_d2:
                si_date_from = st.date_input("From:", value=_si_today.replace(day=1), key="si_dfrom")
            with si_d3:
                si_date_to   = st.date_input("To:", value=_si_today, key="si_dto")

        si_filt = sinv_merged_df.copy() if not sinv_merged_df.empty else pd.DataFrame()
        if not si_filt.empty:
            if si_sel_status != "All" and "Status" in si_filt.columns:
                si_filt = si_filt[si_filt["Status"] == si_sel_status]
            if si_sel_cust != "All" and "Cust. Name" in si_filt.columns:
                si_filt = si_filt[si_filt["Cust. Name"] == si_sel_cust]
            if si_search.strip() and "Invoice No." in si_filt.columns:
                si_filt = si_filt[si_filt["Invoice No."].astype(str).str.contains(si_search.strip(), case=False, na=False)]
            if (si_date_from or si_date_to) and "Date" in si_filt.columns:
                _si_dates = pd.to_datetime(si_filt["Date"], format="%d %b %Y", errors="coerce").dt.date
                if si_date_from: si_filt = si_filt[_si_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= si_date_from)]
                if si_date_to:   si_filt = si_filt[_si_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= si_date_to)]

            # ── Store filtered pipeline → Tab 2 & 3 ──
            _sinv_tab1_inv_nos = set(si_filt["Invoice No."].astype(str).tolist()) if "Invoice No." in si_filt.columns else set()
            sinv_pipeline_raw = [r for r in sinv_raw if str(r.get("IVNUM", "")).strip() in _sinv_tab1_inv_nos]
            st.session_state["sinv_pipeline_raw"] = sinv_pipeline_raw

            si_filt = si_filt.copy()
            si_filt["Tally Match"] = si_filt["Invoice No."].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_sinv_nos else "🆕 Safe to Push"
            )
            si_cols = ["Status", "Tally Match", "Invoice No.", "Date", "Customer No.", "Cust. Name",
                       "Grand Total", "GST", "Line Count", "Parts"]
            st.dataframe(
                fmt_cur(si_filt[[c for c in si_cols if c in si_filt.columns]], "Grand Total", "GST"),
                use_container_width=True, height=480, hide_index=True,
            )
            st.caption(f"ℹ️ {len(si_filt)} invoice(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            # Line items drill-down
            if sinv_has_lines and not sinv_lines_df.empty:
                with st.expander("🔎 Line Items Drill-down"):
                    inv_opts = si_filt["Invoice No."].dropna().astype(str).unique().tolist() if "Invoice No." in si_filt.columns else []
                    if inv_opts:
                        picked = st.selectbox("Select Invoice:", inv_opts, key="si_drill")
                        drill_lines = sinv_lines_df[sinv_lines_df["Invoice No."].astype(str) == picked]
                        if drill_lines.empty:
                            st.caption("No line items found.")
                        else:
                            lcols = [c for c in ["Part Number","Part Description","Quantity","Unit","Unit Price","Discount %","Total Price","Line GST","Warehouse"] if c in drill_lines.columns]
                            st.dataframe(fmt_cur(drill_lines[lcols], "Unit Price","Total Price","Line GST"), use_container_width=True, height=260, hide_index=True)
        else:
            st.markdown('<div class="alert alert-warn">⚠ No invoices returned from Priority ERP.</div>', unsafe_allow_html=True)

    # ── TAB 2: Integrity validation ────────────────────────────────────────────
    with sinv_tab2:
        st.markdown('<p class="sec">Integrity Validation — AINVOICES vs Tally</p>', unsafe_allow_html=True)
        _sinv_pipe = st.session_state.get("sinv_pipeline_raw", None)
        if _sinv_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Sales Invoices</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _sinv_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No invoices match the current filters in the Sales Invoices tab.</div>', unsafe_allow_html=True)
        else:
            si_matrix = []
            for rec in _sinv_pipe:
                inv_ref  = rec.get("IVNUM", "")
                stat_ref = str(rec.get("STATDES") or "").strip()
                customer = str(rec.get("CDES") or "").strip()
                raw_dt   = rec.get("IVDATE", "") or rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("TOTPRICE") or 0)
                in_tally = inv_ref in tally_sinv_nos
                verdict  = ("❌ Duplicate — Already in Tally" if in_tally
                            else ("✅ Safe to Push (Final)" if stat_ref == SINV_PUSH_STATUS
                                  else f"🚫 Not Eligible ({stat_ref})"))
                si_matrix.append({
                    "Verdict":     verdict,
                    "Invoice No.": inv_ref,
                    "Date":        date_str,
                    "Customer":    customer,
                    "Amount":      amount,
                    "Status":      stat_ref,
                    "Tally Match": "Found" if in_tally else "Not Found",
                })
            st.dataframe(pd.DataFrame(si_matrix), use_container_width=True, hide_index=True)
            safe_n = sum(1 for r in si_matrix if "Safe to Push" in r["Verdict"])
            dup_n  = sum(1 for r in si_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in si_matrix if "Not Eligible" in r["Verdict"])
            st.caption(f"✅ {safe_n} safe to push · ❌ {dup_n} duplicate(s) · 🚫 {skip_n} ineligible")

    # ── TAB 3: Tally Sync ──────────────────────────────────────────────────────
    with sinv_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Final Sales Invoices</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">'
            'Only <b>Final</b> invoices are pushed as <b>Sales Invoice</b> vouchers (ISINVOICE=Yes).<br>'
            'Other statuses are shown for reference only and are never pushed.'
            '</div>', unsafe_allow_html=True)

        sinv_pipeline3 = st.session_state.get("sinv_pipeline_raw", sinv_raw)
        sinv_pool = [r for r in sinv_pipeline3 if str(r.get("STATDES") or "").strip() == SINV_PUSH_STATUS]

        sinv_hide_dup = st.checkbox("Hide invoices already in Tally", value=True, key="sinv_hide_dup")
        if sinv_hide_dup:
            sinv_pool = [r for r in sinv_pool if str(r.get("IVNUM", "")).strip() not in tally_sinv_nos]

        st.caption(f"**{len(sinv_pool)}** Final invoice(s) in queue.")

        if not sinv_pool:
            st.markdown('<div class="alert alert-success">✅ All Final invoices are already in Tally — nothing to push.</div>', unsafe_allow_html=True)
        else:
            selected_sinv = []
            for rec in sinv_pool:
                inv_id   = rec.get("IVNUM", "?")
                cust_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("TOTPRICE") or 0)
                n_lines  = len(rec.get(SINV_SUBFORM, []))
                is_dup   = inv_id in tally_sinv_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(f"**{inv_id}** — {cust_lbl} — {val_lbl} — {n_lines} line(s){warn}",
                               value=not is_dup, key=f"sinv_chk_{inv_id}"):
                    selected_sinv.append(rec)

            st.markdown("---")
            sinv_dry = st.checkbox("Dry run (preview only)", value=False, key="sinv_dry")
            if st.button(
                f"{'🧪 Dry Run' if sinv_dry else '🚀 Push'} {len(selected_sinv)} Sales Invoice(s) to Tally",
                key="sinv_push_btn",
            ):
                if not selected_sinv:
                    st.warning("No invoices selected.")
                else:
                    sinv_results = run_sinv_push(selected_sinv, sinv_dry, "SINV-Final")
                    # Render results
                    st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
                    df_res = pd.DataFrame(sinv_results)
                    res_cols = ["Invoice No", "Customer", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
                    st.dataframe(df_res[[c for c in res_cols if c in df_res.columns]], use_container_width=True, hide_index=True)
                    ok_n  = sum(1 for r in sinv_results if "✅" in str(r.get("Result", "")))
                    err_n = sum(1 for r in sinv_results if "❌" in str(r.get("Result", "")))
                    if sinv_dry:
                        st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
                    elif ok_n:
                        st.markdown(f'<div class="alert alert-success">✅ {ok_n} Sales Invoice(s) created in Tally. {err_n} error(s).</div>', unsafe_allow_html=True)
                    if err_n and not sinv_dry:
                        st.markdown(
                            f'<div class="alert alert-error">❌ {err_n} failed — verify:<br>'
                            f'• Tally Gateway active on port 9000<br>'
                            f'• "Sales" voucher type exists in Tally<br>'
                            f'• Ledger <code>{LEDGER_SALES}</code> exists under Sales Accounts<br>'
                            f'• Customer ledger exists under Sundry Debtors</div>',
                            unsafe_allow_html=True)
                    if "push_log" not in st.session_state: st.session_state.push_log = []
                    st.session_state.push_log.extend(sinv_results)

            # XML preview expander
            with st.expander("🔬 Preview XML for selected invoices"):
                for rec in selected_sinv[:3]:   # preview first 3 to avoid flooding
                    inv_id = rec.get("IVNUM", "?")
                    xml_preview = build_sinv_xml(rec)
                    st.markdown(f"**{inv_id}** — {rec.get('CDES', '')}")
                    st.code(xml_preview, language="xml")

elif active_module == "OTC Sales Invoices Module":

    with st.spinner("Fetching OTC Sales Invoices from Priority ERP (EINVOICES)..."):
        tally_otc_nos = query_daybook_by_type(OTC_TALLY_VCH_TYPE)
        tally_otc_nos = tally_otc_nos | st.session_state.get("otc_tally_nos_override", set())
        try:
            otc_raw, otc_expected_count = fetch_otc_sales_invoices()
            otc_header_df = build_otc_header_df(otc_raw) if otc_raw else pd.DataFrame()
            otc_lines_df = build_otc_lines_df(otc_raw) if otc_raw else pd.DataFrame()
            otc_merged_df = build_otc_merged_df(otc_header_df, otc_lines_df) if not otc_header_df.empty else pd.DataFrame()
            otc_fetch_err = None
        except Exception as e:
            otc_fetch_err = str(e)
            otc_raw = []
            otc_expected_count = None
            otc_header_df = pd.DataFrame()
            otc_lines_df = pd.DataFrame()
            otc_merged_df = pd.DataFrame()

    if otc_fetch_err:
        st.markdown(f'<div class="alert alert-error">Priority API Error (EINVOICES): {otc_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if otc_expected_count is not None and len(otc_raw) != int(otc_expected_count):
        st.markdown(
            f'<div class="alert alert-warn">Priority returned {otc_expected_count} record(s), '
            f'but only {len(otc_raw)} were downloaded. Pagination may have been interrupted.</div>',
            unsafe_allow_html=True,
        )

    otc_total = len(otc_header_df) if not otc_header_df.empty else 0
    otc_final = int(otc_header_df["Status"].fillna("").str.strip().str.upper().eq(OTC_STATUS_GATE.upper()).sum()) if "Status" in otc_header_df.columns else 0
    otc_synced = sum(
        1 for n in otc_header_df["Invoice No."].dropna().astype(str).unique()
        if str(n).strip() in tally_otc_nos
    ) if "Invoice No." in otc_header_df.columns else 0
    otc_pending = max(0, otc_final - otc_synced)
    otc_amt = otc_header_df["Grand Total"].sum() if "Grand Total" in otc_header_df.columns else 0

    if not otc_header_df.empty:
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total OTC Invoices</div><div class="kpi-count">{otc_total}</div><div class="kpi-amount">{fmt_inr(otc_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">Final - Ready</div><div class="kpi-count">{otc_final}</div><div class="kpi-amount">Eligible to push</div></div>
            <div class="kpi kpi-final"><div class="kpi-label">Synced</div><div class="kpi-count">{otc_synced}</div><div class="kpi-amount">Sales vouchers in Tally</div></div>
            <div class="kpi kpi-confirmed"><div class="kpi-label">Pending</div><div class="kpi-count">{otc_pending}</div><div class="kpi-amount">Awaiting transport</div></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                margin:8px 0 18px 0;display:flex;gap:24px;flex-wrap:wrap;font-size:13px;color:#c9d1d9">
        <span><b>Final</b> OTC invoices -> Tally <b>Sales Invoice</b> (ISINVOICE=Yes)</span>
        <span>Header: EINVOICES &nbsp;|&nbsp; Lines: EINVOICEITEMS_SUBFORM</span>
        <span>Party ledger: Sundry Debtors &nbsp;|&nbsp; Sales ledger: Sales Account</span>
    </div>""", unsafe_allow_html=True)

    otc_tab1, otc_tab2, otc_tab3 = st.tabs([
        f"OTC Sales Invoices ({len(otc_merged_df) if not otc_merged_df.empty else 0})",
        "Integrity Validation Grid",
        f"Tally Sync ({otc_pending} Pending)",
    ])

    with otc_tab1:
        st.markdown('<p class="sec">OTC Sales Invoices - EINVOICES</p>', unsafe_allow_html=True)
        otc_f1, otc_f2, otc_f3 = st.columns([2, 2, 4])
        with otc_f1:
            _otc_statuses = ["All"] + (sorted(otc_header_df["Status"].dropna().unique().tolist()) if "Status" in otc_header_df.columns else [])
            otc_sel_status = st.selectbox("Status:", _otc_statuses, key="otc_status")
        with otc_f2:
            _otc_customers = ["All"] + (sorted(otc_header_df["Customer Name"].dropna().unique().tolist()) if "Customer Name" in otc_header_df.columns else [])
            otc_sel_cust = st.selectbox("Customer:", _otc_customers, key="otc_customer")
        with otc_f3:
            otc_search = st.text_input("Search Invoice / Customer:", placeholder="e.g. OTC-2026-001", key="otc_search")

        otc_d1, otc_d2, otc_d3 = st.columns([2, 2, 4])
        with otc_d1:
            _otc_today = datetime.today().date()
            otc_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="otc_date_preset")
        otc_date_from = otc_date_to = None
        if otc_date_preset == "Today":
            otc_date_from = otc_date_to = _otc_today
        elif otc_date_preset == "Yesterday":
            otc_date_from = otc_date_to = _otc_today - timedelta(days=1)
        elif otc_date_preset == "Last 7 Days":
            otc_date_from = _otc_today - timedelta(days=6)
            otc_date_to = _otc_today
        elif otc_date_preset == "This Month":
            otc_date_from = _otc_today.replace(day=1)
            otc_date_to = _otc_today
        elif otc_date_preset == "Custom Range":
            with otc_d2:
                otc_date_from = st.date_input("From:", value=_otc_today.replace(day=1), key="otc_date_from")
            with otc_d3:
                otc_date_to = st.date_input("To:", value=_otc_today, key="otc_date_to")
        else:
            with otc_d2:
                st.caption("Showing all dates")

        otc_filt = otc_merged_df.copy() if not otc_merged_df.empty else pd.DataFrame()
        if not otc_filt.empty:
            if otc_sel_status != "All" and "Status" in otc_filt.columns:
                otc_filt = otc_filt[otc_filt["Status"] == otc_sel_status]
            if otc_sel_cust != "All" and "Customer Name" in otc_filt.columns:
                otc_filt = otc_filt[otc_filt["Customer Name"] == otc_sel_cust]
            if otc_search.strip() and "Invoice No." in otc_filt.columns:
                _needle = otc_search.strip()
                _mask = (
                    otc_filt["Invoice No."].astype(str).str.contains(_needle, case=False, na=False)
                    | otc_filt.get("Customer Name", pd.Series("", index=otc_filt.index)).astype(str).str.contains(_needle, case=False, na=False)
                )
                otc_filt = otc_filt[_mask]
            if (otc_date_from or otc_date_to) and "Date" in otc_filt.columns:
                _otc_dates = pd.to_datetime(otc_filt["Date"], format="%d %b %Y", errors="coerce").dt.date
                if otc_date_from:
                    otc_filt = otc_filt[_otc_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= otc_date_from)]
                if otc_date_to:
                    otc_filt = otc_filt[_otc_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= otc_date_to)]

            _otc_tab1_inv_nos = set(otc_filt["Invoice No."].astype(str).tolist()) if "Invoice No." in otc_filt.columns else set()
            otc_pipeline_raw = [r for r in otc_raw if str(r.get("IVNUM", "")).strip() in _otc_tab1_inv_nos]
            st.session_state["otc_pipeline_raw"] = otc_pipeline_raw

            otc_filt = otc_filt.copy()
            otc_filt["Tally Match"] = otc_filt["Invoice No."].apply(
                lambda x: "Already in Tally" if str(x).strip() in tally_otc_nos else "Safe to Push"
            )
            otc_cols = ["Status", "Tally Match", "Invoice No.", "Date", "Customer No.", "Customer Name",
                        "Taxable Total", "GST Amount", "Grand Total", "Line Count"]
            st.dataframe(
                fmt_cur(otc_filt[[c for c in otc_cols if c in otc_filt.columns]], "Taxable Total", "GST Amount", "Grand Total"),
                use_container_width=True,
                height=420,
                hide_index=True,
            )
            st.caption(f"{len(otc_filt)} OTC invoice(s) shown - these flow into the Integrity Validation and Tally Sync tabs.")
        else:
            st.session_state["otc_pipeline_raw"] = []
            st.markdown('<div class="alert alert-warn">No OTC invoices match the current filters.</div>', unsafe_allow_html=True)

    with otc_tab2:
        st.markdown('<p class="sec">Integrity Validation - EINVOICES vs Tally</p>', unsafe_allow_html=True)
        _otc_pipe = st.session_state.get("otc_pipeline_raw", None)
        if _otc_pipe is None:
            st.markdown('<div class="alert alert-warn">Visit the OTC Sales Invoices tab first to apply filters - then come back here.</div>', unsafe_allow_html=True)
        elif not _otc_pipe:
            st.markdown('<div class="alert alert-warn">No OTC invoices match the current filters.</div>', unsafe_allow_html=True)
        else:
            otc_matrix = []
            _otc_safe_nos = set()
            for rec in _otc_pipe:
                inv_ref = str(rec.get("IVNUM", "")).strip()
                stat_ref = str(rec.get("STATDES") or "").strip()
                customer = str(rec.get("CDES") or "").strip()
                in_tally = inv_ref in tally_otc_nos
                lines = rec.get(OTC_SUBFORM, [])
                if in_tally:
                    verdict = "Duplicate - Already in Tally"
                elif stat_ref.upper() == OTC_STATUS_GATE.upper():
                    verdict = "Safe to Push (Final)"
                    _otc_safe_nos.add(inv_ref)
                else:
                    verdict = f"Not Eligible ({stat_ref})"
                otc_matrix.append({
                    "Verdict": verdict,
                    "Invoice No.": inv_ref,
                    "Status": stat_ref,
                    "Customer": customer,
                    "Amount": fmt_inr(rec.get("TOTPRICE") or 0),
                    "Line Count": len(lines),
                    "Tally Match": "Found" if in_tally else "Not Found",
                })
            st.session_state["otc_safe_inv_nos"] = _otc_safe_nos
            st.dataframe(pd.DataFrame(otc_matrix), use_container_width=True, hide_index=True)
            st.caption(f"{len(_otc_safe_nos)} OTC invoice(s) cleared integrity and will appear in Tally Sync.")

    with otc_tab3:
        st.markdown('<p class="sec">Tally Sync - Push Final OTC Sales Invoices</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">Only <b>Final</b> OTC invoices that passed integrity validation are shown here. '
            'Duplicate invoice numbers already found in Tally are excluded.</div>',
            unsafe_allow_html=True,
        )

        _otc_pipe3 = st.session_state.get("otc_pipeline_raw", otc_raw)
        _otc_safe_nos3 = st.session_state.get("otc_safe_inv_nos", None)
        if _otc_safe_nos3 is None:
            _otc_safe_nos3 = {
                str(r.get("IVNUM", "")).strip() for r in _otc_pipe3
                if str(r.get("STATDES") or "").strip().upper() == OTC_STATUS_GATE.upper()
                and str(r.get("IVNUM", "")).strip() not in tally_otc_nos
            }

        otc_pool = [
            r for r in _otc_pipe3
            if str(r.get("IVNUM", "")).strip() in _otc_safe_nos3
            and str(r.get("STATDES") or "").strip().upper() == OTC_STATUS_GATE.upper()
            and str(r.get("IVNUM", "")).strip() not in tally_otc_nos
        ]

        if otc_date_from or otc_date_to:
            def _otc_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("IVDATE") or r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except Exception:
                    return None
            otc_pool = [
                r for r in otc_pool
                if (lambda d: d is not None and (not otc_date_from or d >= otc_date_from) and (not otc_date_to or d <= otc_date_to))(_otc_rec_date(r))
            ]

        st.caption(f"{len(otc_pool)} Final OTC invoice(s) in queue.")
        if not otc_pool:
            st.markdown('<div class="alert alert-success">All staged Final OTC invoices are already synced or blocked by filters.</div>', unsafe_allow_html=True)
        else:
            selected_otc = []
            for rec in otc_pool:
                inv_id = str(rec.get("IVNUM", "")).strip()
                label = f"**{inv_id}** - {rec.get('CDES', '')} - {fmt_inr(rec.get('TOTPRICE') or 0)} [{len(rec.get(OTC_SUBFORM, []))} line(s)]"
                if st.checkbox(label, value=True, key=f"otc_chk_{inv_id}"):
                    selected_otc.append(rec)

            st.markdown("---")
            otc_dry = st.checkbox("Dry run (preview only)", value=False, key="otc_dry")
            if st.button(f"{'Dry Run' if otc_dry else 'Push'} {len(selected_otc)} OTC Sales Invoice(s) to Tally", key="otc_push_btn"):
                if not selected_otc:
                    st.warning("No OTC invoices selected.")
                else:
                    otc_results = run_otc_push(selected_otc, otc_dry, "OTC-Final")
                    st.session_state["otc_last_push_results"] = otc_results
                    if not otc_dry:
                        pushed_nos = {str(r.get("Invoice No", "")).strip() for r in otc_results if "OK" in str(r.get("Result", ""))}
                        st.session_state["otc_tally_nos_override"] = st.session_state.get("otc_tally_nos_override", set()) | pushed_nos

            with st.expander("Preview XML for selected OTC invoices"):
                for rec in selected_otc[:3]:
                    st.markdown(f"**{rec.get('IVNUM')}**")
                    st.code(build_otc_sinv_xml(rec), language="xml")

        last_otc_results = st.session_state.get("otc_last_push_results", [])
        if last_otc_results:
            st.markdown('<p class="sec">Last OTC Push Results</p>', unsafe_allow_html=True)
            otc_res_df = pd.DataFrame(last_otc_results)
            otc_res_cols = ["Invoice No", "Customer", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
            st.dataframe(otc_res_df[[c for c in otc_res_cols if c in otc_res_df.columns]], use_container_width=True, hide_index=True)

elif active_module == "Vendor Invoices Module":

    with st.spinner("Fetching Vendor Invoices from Priority ERP (INVOICES)…"):
        tally_vinv_nos = query_daybook_by_type("Purchase")
        try:
            vinv_raw, vinv_has_lines = fetch_vendor_invoices()
            vinv_header_df = build_vinv_header_df(vinv_raw) if vinv_raw else pd.DataFrame()
            vinv_lines_df  = build_vinv_lines_df(vinv_raw)  if vinv_raw else pd.DataFrame()
            vinv_merged_df = build_vinv_merged_df(vinv_header_df, vinv_lines_df) if not vinv_header_df.empty else pd.DataFrame()
            vinv_fetch_err = None
        except Exception as e:
            vinv_fetch_err = str(e); vinv_raw = []; vinv_header_df = pd.DataFrame()
            vinv_lines_df = pd.DataFrame(); vinv_merged_df = pd.DataFrame(); vinv_has_lines = False

    if vinv_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error (INVOICES): {vinv_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if not vinv_header_df.empty:
        vinv_total = len(vinv_header_df)
        vinv_final = int(vinv_header_df["Status"].eq(VINV_PUSH_STATUS).sum()) if "Status" in vinv_header_df.columns else 0
        vinv_other = vinv_total - vinv_final
        vinv_amt   = vinv_header_df["Amount Owing"].sum() if "Amount Owing" in vinv_header_df.columns else 0
        vinv_amt_f = (vinv_header_df[vinv_header_df["Status"] == VINV_PUSH_STATUS]["Amount Owing"].sum()
                      if "Amount Owing" in vinv_header_df.columns and "Status" in vinv_header_df.columns else 0)
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Vendor Invoices</div><div class="kpi-count">{vinv_total}</div><div class="kpi-amount">{fmt_inr(vinv_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">✅ Final — Ready to Push</div><div class="kpi-count">{vinv_final}</div><div class="kpi-amount">{fmt_inr(vinv_amt_f)}</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">⏳ Other Statuses</div><div class="kpi-count">{vinv_other}</div><div class="kpi-amount">Not pushed</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_vinv_nos)}</div><div class="kpi-amount">Purchase vouchers in Tally</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span>🟡 <b style="color:#e3b341">Final</b> → Tally <b>Purchase Invoice</b> (ISINVOICE=Yes)</span>
            <span>⚙ Header: INVOICES &nbsp;|&nbsp; Lines: INVOICEITEMS</span>
            <span>💰 Party ledger: Sundry Creditors &nbsp;|&nbsp; Purchase ledger: Purchase Account</span>
        </div>""", unsafe_allow_html=True)

    vinv_tab1, vinv_tab2, vinv_tab3 = st.tabs([
        f"🧾 Vendor Invoices ({len(vinv_merged_df) if not vinv_merged_df.empty else 0})",
        "🔍 Integrity Validation Grid",
        f"🚀 Tally Sync ({vinv_final if not vinv_header_df.empty else 0} Final)",
    ])

    # ── TAB 1 ────────────────────────────────────────────────────────────────
    with vinv_tab1:
        st.markdown('<p class="sec">Vendor Invoices — INVOICES</p>', unsafe_allow_html=True)

        vi_f1, vi_f2, vi_f3 = st.columns([2, 2, 4])
        with vi_f1:
            _vinv_statuses = ["All"] + (sorted(vinv_header_df["Status"].dropna().unique().tolist())
                                        if "Status" in vinv_header_df.columns else [])
            vi_sel_status = st.selectbox("Status:", _vinv_statuses, key="vi_status")
        with vi_f2:
            _vinv_vends = ["All"] + (sorted(vinv_header_df["Vendor Name"].dropna().unique().tolist())
                                     if "Vendor Name" in vinv_header_df.columns else [])
            vi_sel_vend = st.selectbox("Vendor:", _vinv_vends, key="vi_vend")
        with vi_f3:
            vi_search = st.text_input("Search Invoice No. / Vendor:", placeholder="e.g. VI26000001", key="vi_search")

        vi_d1, vi_d2, vi_d3 = st.columns([2, 2, 4])
        with vi_d1:
            _vi_today = datetime.today().date()
            vi_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="vi_date")
        vi_date_from = vi_date_to = None
        if vi_date_preset == "Today":
            vi_date_from = vi_date_to = _vi_today
        elif vi_date_preset == "Yesterday":
            from datetime import timedelta
            vi_date_from = vi_date_to = _vi_today - timedelta(days=1)
        elif vi_date_preset == "Last 7 Days":
            from datetime import timedelta
            vi_date_from = _vi_today - timedelta(days=6); vi_date_to = _vi_today
        elif vi_date_preset == "This Month":
            vi_date_from = _vi_today.replace(day=1); vi_date_to = _vi_today
        elif vi_date_preset == "Custom Range":
            with vi_d2:
                vi_date_from = st.date_input("From:", value=_vi_today.replace(day=1), key="vi_dfrom")
            with vi_d3:
                vi_date_to   = st.date_input("To:", value=_vi_today, key="vi_dto")

        vi_filt = vinv_merged_df.copy() if not vinv_merged_df.empty else pd.DataFrame()
        if not vi_filt.empty:
            if vi_sel_status != "All" and "Status" in vi_filt.columns:
                vi_filt = vi_filt[vi_filt["Status"] == vi_sel_status]
            if vi_sel_vend != "All" and "Vendor Name" in vi_filt.columns:
                vi_filt = vi_filt[vi_filt["Vendor Name"] == vi_sel_vend]
            if vi_search.strip() and "Invoice No." in vi_filt.columns:
                vi_filt = vi_filt[vi_filt["Invoice No."].astype(str).str.contains(vi_search.strip(), case=False, na=False)]
            if (vi_date_from or vi_date_to) and "Date" in vi_filt.columns:
                _vi_dates = pd.to_datetime(vi_filt["Date"], format="%d %b %Y", errors="coerce").dt.date
                if vi_date_from: vi_filt = vi_filt[_vi_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= vi_date_from)]
                if vi_date_to:   vi_filt = vi_filt[_vi_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= vi_date_to)]

            _vinv_tab1_inv_nos = set(vi_filt["Invoice No."].astype(str).tolist()) if "Invoice No." in vi_filt.columns else set()
            vinv_pipeline_raw = [r for r in vinv_raw if str(r.get("IVNUM", "")).strip() in _vinv_tab1_inv_nos]
            st.session_state["vinv_pipeline_raw"] = vinv_pipeline_raw

            vi_filt = vi_filt.copy()
            vi_filt["Tally Match"] = vi_filt["Invoice No."].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_vinv_nos else "🆕 Safe to Push"
            )
            vi_cols = ["Status", "Tally Match", "Invoice No.", "Date", "Vendor No.", "Vendor Name",
                       "Amount Owing", "VAT", "Order Number", "Line Count", "Parts"]
            st.dataframe(
                fmt_cur(vi_filt[[c for c in vi_cols if c in vi_filt.columns]], "Amount Owing", "VAT"),
                use_container_width=True, height=480, hide_index=True,
            )
            st.caption(f"ℹ️ {len(vi_filt)} invoice(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            if vinv_has_lines and not vinv_lines_df.empty:
                with st.expander("🔎 Line Items Drill-down"):
                    inv_opts = vi_filt["Invoice No."].dropna().astype(str).unique().tolist() if "Invoice No." in vi_filt.columns else []
                    if inv_opts:
                        picked = st.selectbox("Select Invoice:", inv_opts, key="vi_drill")
                        drill_lines = vinv_lines_df[vinv_lines_df["Invoice No."].astype(str) == picked]
                        if drill_lines.empty:
                            st.caption("No line items found.")
                        else:
                            lcols = [c for c in ["Part Number","Part Description","Quantity","Unit","Unit Price","Discount %","Total Price","Warehouse"] if c in drill_lines.columns]
                            st.dataframe(fmt_cur(drill_lines[lcols], "Unit Price","Total Price"), use_container_width=True, height=260, hide_index=True)
        else:
            st.markdown('<div class="alert alert-warn">⚠ No vendor invoices returned from Priority ERP.</div>', unsafe_allow_html=True)

    # ── TAB 2: Integrity Validation ───────────────────────────────────────────
    with vinv_tab2:
        st.markdown('<p class="sec">Integrity Validation — INVOICES vs Tally</p>', unsafe_allow_html=True)
        _vinv_pipe = st.session_state.get("vinv_pipeline_raw", None)
        if _vinv_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Vendor Invoices</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _vinv_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No invoices match the current filters in the Vendor Invoices tab.</div>', unsafe_allow_html=True)
        else:
            vi_matrix = []
            _vinv_safe_nos = set()
            for rec in _vinv_pipe:
                inv_ref  = rec.get("IVNUM", "")
                stat_ref = str(rec.get("STATDES") or "").strip()
                vendor   = str(rec.get("CDES") or "").strip()
                raw_dt   = rec.get("IVDATE", "") or rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("TOTPRICE") or 0)
                in_tally = inv_ref in tally_vinv_nos
                verdict  = ("❌ Duplicate — Already in Tally" if in_tally
                            else ("✅ Safe to Push (Final)" if stat_ref == VINV_PUSH_STATUS
                                  else f"🚫 Not Eligible ({stat_ref})"))
                if "Safe to Push" in verdict:
                    _vinv_safe_nos.add(inv_ref)
                vi_matrix.append({
                    "Verdict":     verdict,
                    "Invoice No.": inv_ref,
                    "Date":        date_str,
                    "Vendor":      vendor,
                    "Amount":      amount,
                    "Status":      stat_ref,
                    "Tally Match": "Found" if in_tally else "Not Found",
                })
            st.session_state["vinv_safe_inv_nos"] = _vinv_safe_nos
            st.dataframe(pd.DataFrame(vi_matrix), use_container_width=True, hide_index=True)
            safe_n = sum(1 for r in vi_matrix if "Safe to Push" in r["Verdict"])
            dup_n  = sum(1 for r in vi_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in vi_matrix if "Not Eligible" in r["Verdict"])
            st.caption(f"✅ {safe_n} safe to push · ❌ {dup_n} duplicate(s) · 🚫 {skip_n} ineligible")

    # ── TAB 3: Tally Sync ─────────────────────────────────────────────────────
    with vinv_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Final Vendor Invoices</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">'
            'Only <b>Final</b> vendor invoices are pushed as <b>Purchase Invoice</b> vouchers (ISINVOICE=Yes).<br>'
            'Other statuses are shown for reference only and are never pushed.'
            '</div>', unsafe_allow_html=True)

        vinv_pipeline3  = st.session_state.get("vinv_pipeline_raw", vinv_raw)
        _vinv_safe_nos3 = st.session_state.get("vinv_safe_inv_nos", None)

        if _vinv_safe_nos3 is None:
            _vinv_safe_nos3 = {r.get("IVNUM", "") for r in vinv_pipeline3
                               if str(r.get("STATDES") or "").strip() == VINV_PUSH_STATUS
                               and r.get("IVNUM", "") not in tally_vinv_nos}

        vinv_pool = [r for r in vinv_pipeline3
                     if r.get("IVNUM", "") in _vinv_safe_nos3
                     and str(r.get("STATDES") or "").strip() == VINV_PUSH_STATUS]

        if vi_date_from or vi_date_to:
            def _vi_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("IVDATE") or r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except: return None
            vinv_pool = [r for r in vinv_pool if (lambda d: d is not None and
                         (not vi_date_from or d >= vi_date_from) and
                         (not vi_date_to   or d <= vi_date_to))(_vi_rec_date(r))]
            _vi_date_label = (f"{vi_date_from}" if vi_date_from == vi_date_to
                              else f"{vi_date_from} → {vi_date_to}" if vi_date_from and vi_date_to
                              else f"from {vi_date_from}" if vi_date_from else f"until {vi_date_to}")
            st.markdown(f'<div class="alert alert-info">📅 Date filter active: <b>{vi_date_preset}</b> ({_vi_date_label})</div>', unsafe_allow_html=True)

        st.markdown('<div class="alert alert-info">ℹ️ Only invoices that passed the <b>Integrity Validation</b> step are shown here.</div>', unsafe_allow_html=True)

        vinv_hide_dup = st.checkbox("Hide invoices already in Tally", value=True, key="vinv_hide_dup")
        if vinv_hide_dup:
            vinv_pool = [r for r in vinv_pool if str(r.get("IVNUM", "")).strip() not in tally_vinv_nos]

        st.caption(f"**{len(vinv_pool)}** Final vendor invoice(s) in queue.")

        if not vinv_pool:
            st.markdown('<div class="alert alert-success">✅ All Final vendor invoices are already in Tally — nothing to push.</div>', unsafe_allow_html=True)
        else:
            selected_vinv = []
            for rec in vinv_pool:
                inv_id   = rec.get("IVNUM", "?")
                vend_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("TOTPRICE") or 0)
                n_lines  = len(rec.get(VINV_SUBFORM, []))
                is_dup   = inv_id in tally_vinv_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(f"**{inv_id}** — {vend_lbl} — {val_lbl} — {n_lines} line(s){warn}",
                               value=not is_dup, key=f"vinv_chk_{inv_id}"):
                    selected_vinv.append(rec)

            st.markdown("---")
            vinv_dry = st.checkbox("Dry run (preview only)", value=False, key="vinv_dry")
            if st.button(
                f"{'🧪 Dry Run' if vinv_dry else '🚀 Push'} {len(selected_vinv)} Vendor Invoice(s) to Tally",
                key="vinv_push_btn",
            ):
                if not selected_vinv:
                    st.warning("No invoices selected.")
                else:
                    vinv_results = run_vinv_push(selected_vinv, vinv_dry, "VINV-Final")
                    st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
                    df_res = pd.DataFrame(vinv_results)
                    res_cols = ["Invoice No", "Vendor", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
                    st.dataframe(df_res[[c for c in res_cols if c in df_res.columns]], use_container_width=True, hide_index=True)
                    ok_n  = sum(1 for r in vinv_results if "✅" in str(r.get("Result", "")))
                    err_n = sum(1 for r in vinv_results if "❌" in str(r.get("Result", "")))
                    if vinv_dry:
                        st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
                    elif ok_n:
                        st.markdown(f'<div class="alert alert-success">✅ {ok_n} Purchase Invoice(s) created in Tally. {err_n} error(s).</div>', unsafe_allow_html=True)
                    if err_n and not vinv_dry:
                        st.markdown(
                            f'<div class="alert alert-error">❌ {err_n} failed — verify:<br>'
                            f'• Tally Gateway active on port 9000<br>'
                            f'• "Purchase" voucher type exists in Tally<br>'
                            f'• Ledger <code>{LEDGER_PURCHASE}</code> exists under Purchase Accounts<br>'
                            f'• Vendor ledger exists under Sundry Creditors</div>',
                            unsafe_allow_html=True)
                    if "push_log" not in st.session_state: st.session_state.push_log = []
                    st.session_state.push_log.extend(vinv_results)

            with st.expander("🔬 Preview XML for selected invoices"):
                for rec in selected_vinv[:3]:
                    inv_id = rec.get("IVNUM", "?")
                    xml_preview = build_vinv_xml(rec)
                    st.markdown(f"**{inv_id}** — {rec.get('CDES', '')}")
                    st.code(xml_preview, language="xml")


elif active_module == "Goods Receiving Vouchers":

    with st.spinner("Fetching Goods Receiving Vouchers from Priority ERP (DOCUMENTS_P)…"):
        tally_grv_nos = query_daybook_by_type("Receipt Note")
        # Merge locally-tracked pushed GRV nos so duplicate markers appear immediately
        tally_grv_nos = tally_grv_nos | st.session_state.get("grv_tally_nos_override", set())
        try:
            grv_raw, grv_has_lines = fetch_grv()
            grv_header_df = build_grv_header_df(grv_raw) if grv_raw else pd.DataFrame()
            grv_lines_df  = build_grv_lines_df(grv_raw)  if grv_raw else pd.DataFrame()
            grv_merged_df = build_grv_merged_df(grv_header_df, grv_lines_df) if not grv_header_df.empty else pd.DataFrame()
            grv_fetch_err = None
        except Exception as e:
            grv_fetch_err = str(e); grv_raw = []; grv_header_df = pd.DataFrame()
            grv_lines_df = pd.DataFrame(); grv_merged_df = pd.DataFrame(); grv_has_lines = False

    if grv_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error (DOCUMENTS_P): {grv_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if not grv_header_df.empty:
        grv_total = len(grv_header_df)
        grv_final = int(grv_header_df["Status"].eq(GRV_PUSH_STATUS).sum()) if "Status" in grv_header_df.columns else 0
        grv_other = grv_total - grv_final
        grv_amt   = grv_header_df["Total Amount"].sum() if "Total Amount" in grv_header_df.columns else 0
        grv_amt_f = (grv_header_df[grv_header_df["Status"] == GRV_PUSH_STATUS]["Total Amount"].sum()
                     if "Total Amount" in grv_header_df.columns and "Status" in grv_header_df.columns else 0)
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total GRVs</div><div class="kpi-count">{grv_total}</div><div class="kpi-amount">{fmt_inr(grv_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">✅ Final — Ready to Push</div><div class="kpi-count">{grv_final}</div><div class="kpi-amount">{fmt_inr(grv_amt_f)}</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">⏳ Other Statuses</div><div class="kpi-count">{grv_other}</div><div class="kpi-amount">Not pushed</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_grv_nos)}</div><div class="kpi-amount">Receipt Notes in Tally</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span>🟡 <b style="color:#e3b341">Final</b> → Tally <b>Receipt Note</b> (ISINVOICE=No)</span>
            <span>⚙ Header: DOCUMENTS_P &nbsp;|&nbsp; Lines: TRANSORDER_P_SUBFORM</span>
            <span>💰 Party ledger: Sundry Creditors &nbsp;|&nbsp; Purchase ledger: Purchase Account</span>
        </div>""", unsafe_allow_html=True)

    grv_tab1, grv_tab2, grv_tab3 = st.tabs([
        f"📦 Goods Receiving Vouchers ({len(grv_merged_df) if not grv_merged_df.empty else 0})",
        "🔍 Integrity Validation Grid",
        f"🚀 Tally Sync ({grv_final if not grv_header_df.empty else 0} Final)",
    ])

    # ── TAB 1: GRV list ───────────────────────────────────────────────────────
    with grv_tab1:
        st.markdown('<p class="sec">Goods Receiving Vouchers — DOCUMENTS_P</p>', unsafe_allow_html=True)

        # Debug: show which subform key was resolved and raw record sample
        with st.expander("🔧 API Debug — Subform Resolution", expanded=False):
            st.markdown(f"**Resolved subform key:** `{GRV_RESOLVED_SUBFORM}`")
            st.markdown(f"**Has line items:** `{grv_has_lines}`")
            if grv_raw:
                first = grv_raw[0]
                all_keys = list(first.keys())
                st.markdown(f"**Top-level API keys on first record:** `{all_keys}`")
                st.markdown(f"**GRV No (DOCNO):** `{first.get('DOCNO')}` | **Vendor (CDES):** `{first.get('CDES')}`")
                for alias in GRV_SUBFORM_ALIASES:
                    val = first.get(alias)
                    if val is not None:
                        st.markdown(f"  • `{alias}` → `{type(val).__name__}`, len={len(val) if isinstance(val, list) else 'N/A'}, sample={str(val)[:120]}")
                    else:
                        st.markdown(f"  • `{alias}` → ❌ not present")
            else:
                st.markdown("No records fetched from Priority.")

        # ── Tally Receipt Note XML dump — find exact tag for Receipt Doc No. ──
        with st.expander("🔬 Tally Diagnostic — Export existing Receipt Note XML", expanded=False):
            st.caption("Enter the voucher number of a **manually-entered Receipt Note** in Tally to inspect its raw XML and find the correct tag for Receipt Doc No.")
            diag_vch_no = st.text_input("Receipt Note Voucher No. (as it appears in Tally):", key="diag_vch_no", placeholder="e.g. RN-001")
            if st.button("Export from Tally", key="diag_export_btn") and diag_vch_no.strip():
                diag_xml = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>Voucher Register</REPORTNAME>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>{TALLY_COMPANY_XML}</SVCURRENTCOMPANY>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      <SVFROMDATE>19000101</SVFROMDATE>
      <SVTODATE>21001231</SVTODATE>
    </STATICVARIABLES>
    <TDL><TDLMESSAGE>
      <REPORT NAME="VchDump"><FORMS>VchDump</FORMS></REPORT>
      <FORM NAME="VchDump"><TOPPARTS>VchDump</TOPPARTS><XMLTAG>VCHDUMP</XMLTAG></FORM>
      <PART NAME="VchDump">
        <TOPLINES>VchDump</TOPLINES>
        <REPEAT>VchDump : VchCol</REPEAT>
        <SCROLLED>Vertical</SCROLLED>
      </PART>
      <LINE NAME="VchDump">
        <FIELDS>F1,F2,F3,F4,F5,F6,F7,F8,F9,F10</FIELDS>
      </LINE>
      <FIELD NAME="F1"><SET>$VoucherTypeName</SET><XMLTAG>VOUCHERTYPENAME</XMLTAG></FIELD>
      <FIELD NAME="F2"><SET>$VoucherNumber</SET><XMLTAG>VOUCHERNUMBER</XMLTAG></FIELD>
      <FIELD NAME="F3"><SET>$Reference</SET><XMLTAG>REFERENCE</XMLTAG></FIELD>
      <FIELD NAME="F4"><SET>$BasicOrderRef</SET><XMLTAG>BASICORDERREF</XMLTAG></FIELD>
      <FIELD NAME="F5"><SET>$BasicShipDocumentRef</SET><XMLTAG>BASICSHIPDOCUMENTREF</XMLTAG></FIELD>
      <FIELD NAME="F6"><SET>$BasicDocumentRef</SET><XMLTAG>BASICDOCUMENTREF</XMLTAG></FIELD>
      <FIELD NAME="F7"><SET>$BasicPurchaseOrderNo</SET><XMLTAG>BASICPURCHASEORDERNO</XMLTAG></FIELD>
      <FIELD NAME="F8"><SET>$BasicShipVoucherNo</SET><XMLTAG>BASICSHIPVOUCHERNO</XMLTAG></FIELD>
      <FIELD NAME="F9"><SET>$BasicGoodsReceiptNo</SET><XMLTAG>BASICGOODSRECEIPTNO</XMLTAG></FIELD>
      <FIELD NAME="F10"><SET>$OtherReference</SET><XMLTAG>OTHERREFERENCE</XMLTAG></FIELD>
      <COLLECTION NAME="VchCol">
        <TYPE>Vouchers</TYPE>
        <FILTERS>FltVch</FILTERS>
      </COLLECTION>
      <SYSTEM TYPE="Formulae" NAME="FltVch">
        $VoucherNumber = "{diag_vch_no.strip()}" AND $VoucherTypeName = "Receipt Note"
      </SYSTEM>
    </TDLMESSAGE></TDL>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""
                try:
                    diag_resp = requests.post(TALLY_URL, data=diag_xml.encode("utf-8"),
                                              headers={"Content-Type": "application/xml"}, timeout=10)
                    st.markdown(f"**HTTP Status:** `{diag_resp.status_code}`")
                    st.code(diag_resp.text, language="xml")
                    # Extract and highlight the key fields
                    for tag in ["BASICORDERREF", "BASICSHIPDOCUMENTREF", "BASICDOCUMENTREF",
                                "BASICPURCHASEORDERNO", "BASICSHIPVOUCHERNO",
                                "BASICGOODSRECEIPTNO", "OTHERREFERENCE", "REFERENCE"]:
                        import re as _re
                        m = _re.search(rf"<{tag}>(.*?)</{tag}>", diag_resp.text, _re.I)
                        val = m.group(1).strip() if m else "— empty / not found —"
                        icon = "✅" if m and m.group(1).strip() else "❌"
                        st.markdown(f"{icon} `{tag}` → **{val}**")
                except Exception as ex:
                    st.error(f"Could not reach Tally: {ex}")

        gr_f1, gr_f2, gr_f3 = st.columns([2, 2, 4])
        with gr_f1:
            _grv_statuses = ["All"] + (sorted(grv_header_df["Status"].dropna().unique().tolist())
                                       if "Status" in grv_header_df.columns else [])
            gr_sel_status = st.selectbox("Status:", _grv_statuses, key="gr_status")
        with gr_f2:
            _grv_vends = ["All"] + (sorted(grv_header_df["Vendor Name"].dropna().unique().tolist())
                                    if "Vendor Name" in grv_header_df.columns else [])
            gr_sel_vend = st.selectbox("Vendor:", _grv_vends, key="gr_vend")
        with gr_f3:
            gr_search = st.text_input("Search GRV No. / Vendor:", placeholder="e.g. GR26000001", key="gr_search")

        gr_d1, gr_d2, gr_d3 = st.columns([2, 2, 4])
        with gr_d1:
            _gr_today = datetime.today().date()
            gr_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="gr_date")
        gr_date_from = gr_date_to = None
        if gr_date_preset == "Today":
            gr_date_from = gr_date_to = _gr_today
        elif gr_date_preset == "Yesterday":
            from datetime import timedelta
            gr_date_from = gr_date_to = _gr_today - timedelta(days=1)
        elif gr_date_preset == "Last 7 Days":
            from datetime import timedelta
            gr_date_from = _gr_today - timedelta(days=6); gr_date_to = _gr_today
        elif gr_date_preset == "This Month":
            gr_date_from = _gr_today.replace(day=1); gr_date_to = _gr_today
        elif gr_date_preset == "Custom Range":
            with gr_d2:
                gr_date_from = st.date_input("From:", value=_gr_today.replace(day=1), key="gr_dfrom")
            with gr_d3:
                gr_date_to   = st.date_input("To:", value=_gr_today, key="gr_dto")

        gr_filt = grv_merged_df.copy() if not grv_merged_df.empty else pd.DataFrame()
        if not gr_filt.empty:
            if gr_sel_status != "All" and "Status" in gr_filt.columns:
                gr_filt = gr_filt[gr_filt["Status"] == gr_sel_status]
            if gr_sel_vend != "All" and "Vendor Name" in gr_filt.columns:
                gr_filt = gr_filt[gr_filt["Vendor Name"] == gr_sel_vend]
            if gr_search.strip() and "GRV No." in gr_filt.columns:
                gr_filt = gr_filt[gr_filt["GRV No."].astype(str).str.contains(gr_search.strip(), case=False, na=False)]
            if (gr_date_from or gr_date_to) and "Date" in gr_filt.columns:
                _gr_dates = pd.to_datetime(gr_filt["Date"], format="%d %b %Y", errors="coerce").dt.date
                if gr_date_from: gr_filt = gr_filt[_gr_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= gr_date_from)]
                if gr_date_to:   gr_filt = gr_filt[_gr_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= gr_date_to)]

            # Store filtered pipeline → Tab 2 & 3
            _grv_tab1_nos = set(gr_filt["GRV No."].astype(str).tolist()) if "GRV No." in gr_filt.columns else set()
            grv_pipeline_raw = [r for r in grv_raw if str(r.get("DOCNO") or r.get("DNAME") or r.get("DOCNUM", "")).strip() in _grv_tab1_nos]
            st.session_state["grv_pipeline_raw"] = grv_pipeline_raw

            gr_filt = gr_filt.copy()
            gr_filt["Tally Match"] = gr_filt["GRV No."].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_grv_nos else "🆕 Safe to Push"
            )
            gr_cols = ["Status", "Tally Match", "GRV No.", "Date", "Vendor No.", "Vendor Name",
                       "Total Amount", "VAT", "PO Reference", "Line Count", "Parts"]
            st.dataframe(
                fmt_cur(gr_filt[[c for c in gr_cols if c in gr_filt.columns]], "Total Amount", "VAT"),
                use_container_width=True, height=480, hide_index=True,
            )
            st.caption(f"ℹ️ {len(gr_filt)} GRV(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            if grv_has_lines and not grv_lines_df.empty:
                with st.expander("🔎 Line Items Drill-down"):
                    grv_opts = gr_filt["GRV No."].dropna().astype(str).unique().tolist() if "GRV No." in gr_filt.columns else []
                    if grv_opts:
                        picked = st.selectbox("Select GRV:", grv_opts, key="gr_drill")
                        drill_lines = grv_lines_df[grv_lines_df["GRV No."].astype(str) == picked]
                        if drill_lines.empty:
                            st.caption("No line items found.")
                        else:
                            lcols = [c for c in ["Part Number","Part Description","Quantity","Unit","Unit Price","Discount %","Total Price","Warehouse","PO Reference","External Part No."] if c in drill_lines.columns]
                            st.dataframe(fmt_cur(drill_lines[lcols], "Unit Price","Total Price"), use_container_width=True, height=260, hide_index=True)
        else:
            st.markdown('<div class="alert alert-warn">⚠ No GRVs returned from Priority ERP.</div>', unsafe_allow_html=True)

    # ── TAB 2: Integrity Validation ───────────────────────────────────────────
    with grv_tab2:
        st.markdown('<p class="sec">Integrity Validation — DOCUMENTS_P vs Tally</p>', unsafe_allow_html=True)
        _grv_pipe = st.session_state.get("grv_pipeline_raw", None)
        if _grv_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Goods Receiving Vouchers</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _grv_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No GRVs match the current filters in the Goods Receiving Vouchers tab.</div>', unsafe_allow_html=True)
        else:
            gr_matrix = []
            _grv_safe_nos = set()
            for rec in _grv_pipe:
                grv_ref  = rec.get("DOCNO") or rec.get("DNAME") or rec.get("DOCNUM", "")
                stat_ref = str(rec.get("STATDES") or "").strip()
                vendor   = str(rec.get("CDES") or "").strip()
                raw_dt   = rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("TOTPRICE") or 0)
                in_tally = grv_ref in tally_grv_nos
                verdict  = ("❌ Duplicate — Already in Tally" if in_tally
                            else ("✅ Safe to Push (Final)" if stat_ref == GRV_PUSH_STATUS
                                  else f"🚫 Not Eligible ({stat_ref})"))
                if "Safe to Push" in verdict:
                    _grv_safe_nos.add(grv_ref)
                gr_matrix.append({
                    "Verdict":      verdict,
                    "GRV No.":      grv_ref,
                    "Date":         date_str,
                    "Vendor":       vendor,
                    "Amount":       amount,
                    "Status":       stat_ref,
                    "PO Reference": rec.get("ORDNAME", ""),
                    "Tally Match":  "Found" if in_tally else "Not Found",
                })
            st.session_state["grv_safe_nos"] = _grv_safe_nos
            st.dataframe(pd.DataFrame(gr_matrix), use_container_width=True, hide_index=True)
            safe_n = sum(1 for r in gr_matrix if "Safe to Push" in r["Verdict"])
            dup_n  = sum(1 for r in gr_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in gr_matrix if "Not Eligible" in r["Verdict"])
            st.caption(f"✅ {safe_n} safe to push · ❌ {dup_n} duplicate(s) · 🚫 {skip_n} ineligible")

    # ── TAB 3: Tally Sync ─────────────────────────────────────────────────────
    with grv_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Final GRVs as Receipt Notes</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">' 
            'Only <b>Final</b> GRVs are pushed as <b>Receipt Note</b> vouchers (ISINVOICE=No).<br>'
            'Other statuses are shown for reference only and are never pushed.'
            '</div>', unsafe_allow_html=True)

        grv_pipeline3  = st.session_state.get("grv_pipeline_raw", grv_raw)
        _grv_safe_nos3 = st.session_state.get("grv_safe_nos", None)

        if _grv_safe_nos3 is None:
            _grv_safe_nos3 = {(r.get("DOCNO") or r.get("DNAME") or r.get("DOCNUM", ""))
                              for r in grv_pipeline3
                              if str(r.get("STATDES") or "").strip() == GRV_PUSH_STATUS
                              and (r.get("DOCNO") or r.get("DNAME") or r.get("DOCNUM", "")) not in tally_grv_nos}
        else:
            # Re-validate safe set against live tally_grv_nos — removes any pushed since Tab 2
            _grv_safe_nos3 = {n for n in _grv_safe_nos3 if n not in tally_grv_nos}

        grv_pool = [r for r in grv_pipeline3
                    if (r.get("DOCNO") or r.get("DNAME") or r.get("DOCNUM", "")) in _grv_safe_nos3
                    and str(r.get("STATDES") or "").strip() == GRV_PUSH_STATUS
                    and str(r.get("DOCNO") or r.get("DNAME") or r.get("DOCNUM", "")).strip() not in tally_grv_nos]

        if gr_date_from or gr_date_to:
            def _gr_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except: return None
            grv_pool = [r for r in grv_pool if (lambda d: d is not None and
                        (not gr_date_from or d >= gr_date_from) and
                        (not gr_date_to   or d <= gr_date_to))(_gr_rec_date(r))]
            _gr_date_label = (f"{gr_date_from}" if gr_date_from == gr_date_to
                              else f"{gr_date_from} → {gr_date_to}" if gr_date_from and gr_date_to
                              else f"from {gr_date_from}" if gr_date_from else f"until {gr_date_to}")
            st.markdown(f'<div class="alert alert-info">📅 Date filter active: <b>{gr_date_preset}</b> ({_gr_date_label})</div>', unsafe_allow_html=True)

        st.markdown('<div class="alert alert-info">ℹ️ Only GRVs that passed the <b>Integrity Validation</b> step are shown here.</div>', unsafe_allow_html=True)

        grv_hide_dup = st.checkbox("Hide GRVs already in Tally", value=True, key="grv_hide_dup")
        if grv_hide_dup:
            grv_pool = [r for r in grv_pool if str(r.get("DOCNO", "")).strip() not in tally_grv_nos]

        st.caption(f"**{len(grv_pool)}** Final GRV(s) in queue.")

        selected_grv = []  # initialise here so push-results debug expander can reference it even when pool is empty
        if not grv_pool:
            st.markdown('<div class="alert alert-success">✅ All Final GRVs are already in Tally — nothing to push.</div>', unsafe_allow_html=True)
        else:
            for rec in grv_pool:
                grv_id   = rec.get("DOCNO", "?")
                vend_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("TOTPRICE") or 0)
                n_lines  = len(rec.get(GRV_SUBFORM, []))
                po_lbl   = rec.get("ORDNAME", "")
                is_dup   = grv_id in tally_grv_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                po_tag   = f" — PO: {po_lbl}" if po_lbl else ""
                if st.checkbox(f"**{grv_id}** — {vend_lbl} — {val_lbl} — {n_lines} line(s){po_tag}{warn}",
                               value=not is_dup, key=f"grv_chk_{grv_id}"):
                    selected_grv.append(rec)

            st.markdown("---")
            grv_dry = st.checkbox("Dry run (preview only)", value=False, key="grv_dry")
            if st.button(
                f"{'🧪 Dry Run' if grv_dry else '🚀 Push'} {len(selected_grv)} GRV(s) to Tally as Receipt Notes",
                key="grv_push_btn",
            ):
                if not selected_grv:
                    st.warning("No GRVs selected.")
                else:
                    grv_results = run_grv_push(selected_grv, grv_dry, "GRV-Final")
                    ok_n  = sum(1 for r in grv_results if "✅" in str(r.get("Result", "")))
                    err_n = sum(1 for r in grv_results if "❌" in str(r.get("Result", "")))
                    if "push_log" not in st.session_state: st.session_state.push_log = []
                    st.session_state.push_log.extend(grv_results)
                    # Store results in session state BEFORE rerun so they survive the refresh
                    st.session_state["grv_last_push_results"] = grv_results
                    st.session_state["grv_last_push_dry"]     = grv_dry
                    st.session_state["grv_last_push_ok"]      = ok_n
                    st.session_state["grv_last_push_err"]     = err_n
                    if ok_n and not grv_dry:
                        # Immediately inject pushed GRV nos into session-state tally set
                        pushed_nos = {str(r.get("GRV No", "")).strip() for r in grv_results if "✅" in str(r.get("Result", ""))}
                        _existing = st.session_state.get("grv_tally_nos_override", set())
                        st.session_state["grv_tally_nos_override"] = _existing | pushed_nos
                        # Clear stale safe-set so Tab 1/2/3 re-evaluate with updated tally set
                        for _k in ["grv_safe_nos", "grv_pipeline_raw"]:
                            st.session_state.pop(_k, None)
                        st.cache_data.clear()
                        st.rerun()

            with st.expander("🔬 Preview XML for selected GRVs"):
                for rec in selected_grv[:3]:
                    grv_id = rec.get("DOCNO", "?")
                    xml_preview = build_grv_xml(rec)
                    st.markdown(f"**{grv_id}** — {rec.get('CDES', '')}")
                    st.code(xml_preview, language="xml")

        # ── Display last push results — OUTSIDE if/else so it always shows after a push ──
        _grv_lpr = st.session_state.get("grv_last_push_results")
        if _grv_lpr:
            _dry  = st.session_state.get("grv_last_push_dry", False)
            _ok   = st.session_state.get("grv_last_push_ok",  0)
            _err  = st.session_state.get("grv_last_push_err", 0)
            st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
            df_res = pd.DataFrame(_grv_lpr)
            res_cols = ["GRV No", "Vendor", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
            st.dataframe(df_res[[c for c in res_cols if c in df_res.columns]], use_container_width=True, hide_index=True)
            if _dry:
                st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
            elif _ok:
                st.markdown(f'<div class="alert alert-success">✅ {_ok} Receipt Note(s) created in Tally. {_err} error(s).</div>', unsafe_allow_html=True)
            if _err and not _dry:
                st.markdown(
                    f'<div class="alert alert-error">❌ {_err} failed — verify:<br>'
                    f'• Tally Gateway active on port 9000<br>'
                    f'• "Receipt Note" voucher type exists in Tally<br>'
                    f'• Ledger <code>{LEDGER_PURCHASE}</code> exists under Purchase Accounts<br>'
                    f'• Vendor ledger exists under Sundry Creditors</div>',
                    unsafe_allow_html=True)

            with st.expander("🛠 Debug — Raw Priority API fields (vendor doc number)"):
                st.caption("Use this to identify which field Priority returns for the vendor's document number.")
                vendor_doc_fields = ["BOOKNUM", "IVNUM", "EXTDOCNO", "SUPPREF", "DOCDES", "DNAME", "DOCNO", "DOCNUM"]
                if selected_grv:
                    for rec in selected_grv[:3]:
                        grv_id = rec.get("DOCNO", "?")
                        st.markdown(f"**GRV: {grv_id}**")
                        field_data = {f: rec.get(f, "❌ not returned by API") for f in vendor_doc_fields}
                        st.json(field_data)
                        # All raw fields shown inline (no nested expander — Streamlit doesn't support it)
                        all_scalar_keys = {k: v for k, v in rec.items() if not isinstance(v, list)}
                        st.markdown(f"<small>📋 All raw fields for **{grv_id}**:</small>", unsafe_allow_html=True)
                        st.json(all_scalar_keys)
                        st.divider()
                else:
                    st.caption("Select at least one GRV above to inspect its raw fields.")

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE UI: MULTI GRV INVOICE
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Multi GRV Invoice Module":

    with st.spinner("Fetching Multi GRV Invoices from Priority ERP (PINVOICES)…"):
        tally_vinv_nos = query_daybook_by_type("Purchase")
        # Merge any locally-tracked pushed invoice nos (covers cases where Tally re-query
        # misses newly created vouchers due to voucher-type name filter mismatch)
        tally_vinv_nos = tally_vinv_nos | st.session_state.get("vinv_tally_nos_override", set())
        try:
            vinv_raw, vinv_has_lines = fetch_mgrv_invoices()
            vinv_header_df = build_mgrv_header_df(vinv_raw) if vinv_raw else pd.DataFrame()
            vinv_lines_df  = build_mgrv_lines_df(vinv_raw)  if vinv_raw else pd.DataFrame()
            vinv_merged_df = build_mgrv_merged_df(vinv_header_df, vinv_lines_df) if not vinv_header_df.empty else pd.DataFrame()
            vinv_fetch_err = None
        except Exception as e:
            vinv_fetch_err = str(e); vinv_raw = []; vinv_header_df = pd.DataFrame()
            vinv_lines_df = pd.DataFrame(); vinv_merged_df = pd.DataFrame(); vinv_has_lines = False

    if vinv_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error (PINVOICES): {vinv_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if not vinv_header_df.empty:
        vinv_total = len(vinv_header_df)
        vinv_final = int(vinv_header_df["Status"].eq(MGRV_PUSH_STATUS).sum()) if "Status" in vinv_header_df.columns else 0
        vinv_other = vinv_total - vinv_final
        vinv_amt   = vinv_header_df["Amount Owing"].sum() if "Amount Owing" in vinv_header_df.columns else 0
        vinv_amt_f = (vinv_header_df[vinv_header_df["Status"] == MGRV_PUSH_STATUS]["Amount Owing"].sum()
                      if "Amount Owing" in vinv_header_df.columns and "Status" in vinv_header_df.columns else 0)
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Multi GRV Invoices</div><div class="kpi-count">{vinv_total}</div><div class="kpi-amount">{fmt_inr(vinv_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">✅ Final — Ready to Push</div><div class="kpi-count">{vinv_final}</div><div class="kpi-amount">{fmt_inr(vinv_amt_f)}</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">⏳ Other Statuses</div><div class="kpi-count">{vinv_other}</div><div class="kpi-amount">Not pushed</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_vinv_nos)}</div><div class="kpi-amount">Purchase vouchers in Tally</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span>🟡 <b style="color:#e3b341">Final</b> → Tally <b>Purchase Invoice</b> (ISINVOICE=Yes)</span>
            <span>⚙ Header: PINVOICES &nbsp;|&nbsp; Lines: PINVOICEITEMS</span>
            <span>💰 Party ledger: Sundry Creditors &nbsp;|&nbsp; Purchase ledger: Purchase Account</span>
        </div>""", unsafe_allow_html=True)

    vinv_tab1, vinv_tab2, vinv_tab3 = st.tabs([
        f"🧾 Multi GRV Invoices ({len(vinv_merged_df) if not vinv_merged_df.empty else 0})",
        "🔍 Integrity Validation Grid",
        f"🚀 Tally Sync ({vinv_final if not vinv_header_df.empty else 0} Final)",
    ])

    # ── TAB 1 ────────────────────────────────────────────────────────────────
    with vinv_tab1:
        st.markdown('<p class="sec">Multi GRV Invoices — PINVOICES</p>', unsafe_allow_html=True)

        vi_f1, vi_f2, vi_f3 = st.columns([2, 2, 4])
        with vi_f1:
            _vinv_statuses = ["All"] + (sorted(vinv_header_df["Status"].dropna().unique().tolist())
                                        if "Status" in vinv_header_df.columns else [])
            vi_sel_status = st.selectbox("Status:", _vinv_statuses, key="mgrv_vi_status")
        with vi_f2:
            _vinv_vends = ["All"] + (sorted(vinv_header_df["Vendor Name"].dropna().unique().tolist())
                                     if "Vendor Name" in vinv_header_df.columns else [])
            vi_sel_vend = st.selectbox("Vendor:", _vinv_vends, key="mgrv_vi_vend")
        with vi_f3:
            vi_search = st.text_input("Search Invoice No. / Vendor:", placeholder="e.g. VI26000001", key="mgrv_vi_search")

        vi_d1, vi_d2, vi_d3 = st.columns([2, 2, 4])
        with vi_d1:
            _vi_today = datetime.today().date()
            vi_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="mgrv_vi_date")
        vi_date_from = vi_date_to = None
        if vi_date_preset == "Today":
            vi_date_from = vi_date_to = _vi_today
        elif vi_date_preset == "Yesterday":
            from datetime import timedelta
            vi_date_from = vi_date_to = _vi_today - timedelta(days=1)
        elif vi_date_preset == "Last 7 Days":
            from datetime import timedelta
            vi_date_from = _vi_today - timedelta(days=6); vi_date_to = _vi_today
        elif vi_date_preset == "This Month":
            vi_date_from = _vi_today.replace(day=1); vi_date_to = _vi_today
        elif vi_date_preset == "Custom Range":
            with vi_d2:
                vi_date_from = st.date_input("From:", value=_vi_today.replace(day=1), key="mgrv_vi_dfrom")
            with vi_d3:
                vi_date_to   = st.date_input("To:", value=_vi_today, key="mgrv_vi_dto")

        vi_filt = vinv_merged_df.copy() if not vinv_merged_df.empty else pd.DataFrame()
        if not vi_filt.empty:
            if vi_sel_status != "All" and "Status" in vi_filt.columns:
                vi_filt = vi_filt[vi_filt["Status"] == vi_sel_status]
            if vi_sel_vend != "All" and "Vendor Name" in vi_filt.columns:
                vi_filt = vi_filt[vi_filt["Vendor Name"] == vi_sel_vend]
            if vi_search.strip() and "Invoice No." in vi_filt.columns:
                vi_filt = vi_filt[vi_filt["Invoice No."].astype(str).str.contains(vi_search.strip(), case=False, na=False)]
            if (vi_date_from or vi_date_to) and "Date" in vi_filt.columns:
                _vi_dates = pd.to_datetime(vi_filt["Date"], format="%d %b %Y", errors="coerce").dt.date
                if vi_date_from: vi_filt = vi_filt[_vi_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= vi_date_from)]
                if vi_date_to:   vi_filt = vi_filt[_vi_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= vi_date_to)]

            _vinv_tab1_inv_nos = set(vi_filt["Invoice No."].astype(str).tolist()) if "Invoice No." in vi_filt.columns else set()
            vinv_pipeline_raw = [r for r in vinv_raw if str(r.get("BOOKNUM", "")).strip() in _vinv_tab1_inv_nos]
            st.session_state["vinv_pipeline_raw"] = vinv_pipeline_raw

            vi_filt = vi_filt.copy()
            vi_filt["Tally Match"] = vi_filt["Invoice No."].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_vinv_nos else "🆕 Safe to Push"
            )
            vi_cols = ["Status", "Tally Match", "Invoice No.", "Date", "Vendor No.", "Vendor Name",
                       "Amount Owing", "VAT", "Order Number", "Line Count", "Parts"]
            st.dataframe(
                fmt_cur(vi_filt[[c for c in vi_cols if c in vi_filt.columns]], "Amount Owing", "VAT"),
                use_container_width=True, height=480, hide_index=True,
            )
            st.caption(f"ℹ️ {len(vi_filt)} invoice(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            if vinv_has_lines and not vinv_lines_df.empty:
                with st.expander("🔎 Line Items Drill-down"):
                    inv_opts = vi_filt["Invoice No."].dropna().astype(str).unique().tolist() if "Invoice No." in vi_filt.columns else []
                    if inv_opts:
                        picked = st.selectbox("Select Invoice:", inv_opts, key="mgrv_vi_drill")
                        drill_lines = vinv_lines_df[vinv_lines_df["Invoice No."].astype(str) == picked]
                        if drill_lines.empty:
                            st.caption("No line items found.")
                        else:
                            lcols = [c for c in ["Part Number","Part Description","Quantity","Unit","Unit Price","Discount %","Total Price","Line GST","Warehouse"] if c in drill_lines.columns]
                            st.dataframe(fmt_cur(drill_lines[lcols], "Unit Price","Total Price","Line GST"), use_container_width=True, height=260, hide_index=True)
        else:
            st.markdown('<div class="alert alert-warn">⚠ No Multi GRV invoices returned from Priority ERP.</div>', unsafe_allow_html=True)

    # ── TAB 2: Integrity Validation ───────────────────────────────────────────
    with vinv_tab2:
        st.markdown('<p class="sec">Integrity Validation — PINVOICES vs Tally</p>', unsafe_allow_html=True)
        _vinv_pipe = st.session_state.get("vinv_pipeline_raw", None)
        if _vinv_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Multi GRV Invoices</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _vinv_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No invoices match the current filters in the Multi GRV Invoices tab.</div>', unsafe_allow_html=True)
        else:
            vi_matrix = []
            _vinv_safe_nos = set()
            for rec in _vinv_pipe:
                inv_ref  = rec.get("BOOKNUM", "")
                stat_ref = str(rec.get("STATDES") or "").strip()
                vendor   = str(rec.get("CDES") or rec.get("SUPDES") or "").strip()
                raw_dt   = rec.get("IVDATE", "") or rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("TOTPRICE") or 0)
                in_tally = inv_ref in tally_vinv_nos
                verdict  = ("❌ Duplicate — Already in Tally" if in_tally
                            else ("✅ Safe to Push (Final)" if stat_ref == MGRV_PUSH_STATUS
                                  else f"🚫 Not Eligible ({stat_ref})"))
                if "Safe to Push" in verdict:
                    _vinv_safe_nos.add(inv_ref)

                # ── Tax Rate preview: from global PARTNAME map (primary) ────
                # Uses the same _build_partname_taxrate_map() that build_mgrv_xml uses,
                # so what you see here is exactly what will be pushed to Tally.
                _global_rate_preview = _build_partname_taxrate_map()
                _po_ref_preview = str(rec.get("ORDNAME") or "").strip()
                _lines_preview  = rec.get(MGRV_SUBFORM) or []
                _MISS_PREV = object()
                tax_rate_parts  = []
                for _ln in _lines_preview:
                    _pn = str(_ln.get("PARTNAME") or "").strip()
                    if not _pn:
                        continue
                    # Tier 1: global map — use sentinel to distinguish 0% from unknown
                    _t1 = _global_rate_preview.get(_pn.upper(), _MISS_PREV)
                    if _t1 is not _MISS_PREV:
                        _rate = float(_t1)
                        if _rate == 0.0:
                            tax_rate_parts.append(f"{_pn}: 0% (Exempt)")
                        else:
                            tax_rate_parts.append(f"{_pn}: {_rate:g}%")
                    else:
                        # Tier 2: single-PO lookup (item not seen in any PO/GRV yet)
                        _rate_t2 = 0.0
                        if _po_ref_preview:
                            _po_lkp = _build_po_gst_lookup(_po_ref_preview)
                            _pd = _po_lkp.get(_pn)
                            _rate_t2 = _pd.get("taxrate", 0.0) if _pd else 0.0
                        if _rate_t2 > 0:
                            tax_rate_parts.append(f"{_pn}: {_rate_t2:g}% (from PO)")
                        else:
                            tax_rate_parts.append(f"{_pn}: ⚠ No Rate")
                tax_rate_str = " | ".join(tax_rate_parts) if tax_rate_parts else "—"

                vi_matrix.append({
                    "Verdict":     verdict,
                    "Invoice No.": inv_ref,
                    "Date":        date_str,
                    "Vendor":      vendor,
                    "Amount":      amount,
                    "PO Ref":      _po_ref_preview or "—",
                    "Tax Rate (per item)": tax_rate_str,
                    "Status":      stat_ref,
                    "Tally Match": "Found" if in_tally else "Not Found",
                })
            st.session_state["vinv_safe_inv_nos"] = _vinv_safe_nos
            st.dataframe(pd.DataFrame(vi_matrix), use_container_width=True, hide_index=True)
            safe_n = sum(1 for r in vi_matrix if "Safe to Push" in r["Verdict"])
            dup_n  = sum(1 for r in vi_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in vi_matrix if "Not Eligible" in r["Verdict"])
            no_rate_n = sum(1 for r in vi_matrix if "⚠" in r.get("Tax Rate (per item)", ""))
            caption_parts = [f"✅ {safe_n} safe to push", f"❌ {dup_n} duplicate(s)", f"🚫 {skip_n} ineligible"]
            if no_rate_n:
                caption_parts.append(f"⚠ {no_rate_n} invoice(s) with missing tax rate — check PO link")
            st.caption(" · ".join(caption_parts))

    # ── TAB 3: Tally Sync ─────────────────────────────────────────────────────
    with vinv_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Final Multi GRV Invoices</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">'
            'Only <b>Final</b> Multi GRV invoices are pushed as <b>Purchase Invoice</b> vouchers (ISINVOICE=Yes).<br>'
            'Other statuses are shown for reference only and are never pushed.'
            '</div>', unsafe_allow_html=True)

        vinv_pipeline3  = st.session_state.get("vinv_pipeline_raw", vinv_raw)
        _vinv_safe_nos3 = st.session_state.get("vinv_safe_inv_nos", None)

        if _vinv_safe_nos3 is None:
            _vinv_safe_nos3 = {r.get("BOOKNUM", "") for r in vinv_pipeline3
                               if str(r.get("STATDES") or "").strip() == MGRV_PUSH_STATUS
                               and r.get("BOOKNUM", "") not in tally_vinv_nos}
        else:
            # Re-validate safe set against live tally_vinv_nos — removes any that were
            # pushed since Tab 2 was last visited (prevents stale safe set after a push)
            _vinv_safe_nos3 = {n for n in _vinv_safe_nos3 if n not in tally_vinv_nos}

        vinv_pool = [r for r in vinv_pipeline3
                     if r.get("BOOKNUM", "") in _vinv_safe_nos3
                     and str(r.get("STATDES") or "").strip() == MGRV_PUSH_STATUS
                     and str(r.get("BOOKNUM", "")).strip() not in tally_vinv_nos]

        if vi_date_from or vi_date_to:
            def _vi_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("IVDATE") or r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except: return None
            vinv_pool = [r for r in vinv_pool if (lambda d: d is not None and
                         (not vi_date_from or d >= vi_date_from) and
                         (not vi_date_to   or d <= vi_date_to))(_vi_rec_date(r))]
            _vi_date_label = (f"{vi_date_from}" if vi_date_from == vi_date_to
                              else f"{vi_date_from} → {vi_date_to}" if vi_date_from and vi_date_to
                              else f"from {vi_date_from}" if vi_date_from else f"until {vi_date_to}")
            st.markdown(f'<div class="alert alert-info">📅 Date filter active: <b>{vi_date_preset}</b> ({_vi_date_label})</div>', unsafe_allow_html=True)

        st.markdown('<div class="alert alert-info">ℹ️ Only invoices that passed the <b>Integrity Validation</b> step are shown here.</div>', unsafe_allow_html=True)

        vinv_hide_dup = st.checkbox("Hide invoices already in Tally", value=True, key="mgrv_hide_dup")
        if vinv_hide_dup:
            vinv_pool = [r for r in vinv_pool if str(r.get("BOOKNUM", "")).strip() not in tally_vinv_nos]

        st.caption(f"**{len(vinv_pool)}** Final Multi GRV invoice(s) in queue.")

        if not vinv_pool:
            st.markdown('<div class="alert alert-success">✅ All Final Multi GRV invoices are already in Tally — nothing to push.</div>', unsafe_allow_html=True)
        else:
            selected_vinv = []
            for rec in vinv_pool:
                inv_id   = rec.get("BOOKNUM", "?")
                vend_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("TOTPRICE") or 0)
                n_lines  = len(rec.get(MGRV_SUBFORM, []))
                is_dup   = inv_id in tally_vinv_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(f"**{inv_id}** — {vend_lbl} — {val_lbl} — {n_lines} line(s){warn}",
                               value=not is_dup, key=f"mgrv_chk_{rec.get('IVNUM', inv_id)}"):
                    selected_vinv.append(rec)

            st.markdown("---")
            vinv_dry = st.checkbox("Dry run (preview only)", value=False, key="mgrv_dry")
            if st.button(
                f"{'🧪 Dry Run' if vinv_dry else '🚀 Push'} {len(selected_vinv)} Multi GRV Invoice(s) to Tally",
                key="mgrv_push_btn",
            ):
                if not selected_vinv:
                    st.warning("No invoices selected.")
                else:
                    vinv_results = run_mgrv_push(selected_vinv, vinv_dry, "VINV-Final")
                    ok_n  = sum(1 for r in vinv_results if "✅" in str(r.get("Result", "")))
                    err_n = sum(1 for r in vinv_results if "❌" in str(r.get("Result", "")))
                    if "push_log" not in st.session_state: st.session_state.push_log = []
                    st.session_state.push_log.extend(vinv_results)
                    # Store results + summary flags in session state BEFORE rerun so they
                    # survive the page refresh and are displayed in the block below
                    st.session_state["vinv_last_push_results"] = vinv_results
                    st.session_state["vinv_last_push_dry"]     = vinv_dry
                    st.session_state["vinv_last_push_ok"]      = ok_n
                    st.session_state["vinv_last_push_err"]     = err_n
                    if ok_n and not vinv_dry:
                        # Immediately inject pushed invoice nos into a session-state tally set
                        # so duplicate markers appear right away, independent of Tally re-query
                        pushed_nos = {str(r.get("Invoice No", "")).strip() for r in vinv_results if "✅" in str(r.get("Result", ""))}
                        _existing = st.session_state.get("vinv_tally_nos_override", set())
                        st.session_state["vinv_tally_nos_override"] = _existing | pushed_nos
                        # Clear stale safe-set so Tab 1/2/3 re-evaluate with updated tally set
                        for _k in ["vinv_safe_inv_nos", "vinv_pipeline_raw"]:
                            st.session_state.pop(_k, None)
                        st.cache_data.clear()
                        st.rerun()

            with st.expander("🔬 Preview XML for selected invoices"):
                for rec in selected_vinv[:3]:
                    inv_id = rec.get("BOOKNUM", "?")
                    xml_preview = build_mgrv_xml(rec)
                    st.markdown(f"**{inv_id}** — {rec.get('CDES', '')}")
                    st.code(xml_preview, language="xml")

        # ── Display last push results (outside if/else vinv_pool — always visible after push) ──
        _lpr = st.session_state.get("vinv_last_push_results")
        if _lpr:
            _dry  = st.session_state.get("vinv_last_push_dry", False)
            _ok   = st.session_state.get("vinv_last_push_ok",  0)
            _err  = st.session_state.get("vinv_last_push_err", 0)
            st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
            df_res = pd.DataFrame(_lpr)
            res_cols = ["Invoice No", "Vendor", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
            st.dataframe(df_res[[c for c in res_cols if c in df_res.columns]], use_container_width=True, hide_index=True)
            if _dry:
                st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
            elif _ok:
                st.markdown(f'<div class="alert alert-success">✅ {_ok} Purchase Invoice(s) created in Tally from Multi GRV. {_err} error(s).</div>', unsafe_allow_html=True)
            if _err and not _dry:
                st.markdown(
                    f'<div class="alert alert-error">❌ {_err} failed — verify:<br>'
                    f'• Tally Gateway active on port 9000<br>'
                    f'• "Purchase" voucher type exists in Tally<br>'
                    f'• Ledger <code>{LEDGER_PURCHASE}</code> exists under Purchase Accounts<br>'
                    f'• Vendor ledger exists under Sundry Creditors</div>',
                    unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE UI: MULTI SHIPMENT INVOICE
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Multi Shipment Invoice Module":

    with st.spinner("Fetching Multi Shipment Invoices from Priority ERP (CINVOICES)…"):
        tally_msinv_nos = query_daybook_by_type("Sales")
        tally_msinv_nos = tally_msinv_nos | st.session_state.get("msinv_tally_nos_override", set())
        try:
            msinv_raw, msinv_has_lines = fetch_msinv_invoices()
            msinv_header_df = build_msinv_header_df(msinv_raw) if msinv_raw else pd.DataFrame()
            msinv_lines_df  = build_msinv_lines_df(msinv_raw)  if msinv_raw else pd.DataFrame()
            msinv_merged_df = build_msinv_merged_df(msinv_header_df, msinv_lines_df) if not msinv_header_df.empty else pd.DataFrame()
            msinv_fetch_err = None
        except Exception as e:
            msinv_fetch_err = str(e); msinv_raw = []; msinv_header_df = pd.DataFrame()
            msinv_lines_df = pd.DataFrame(); msinv_merged_df = pd.DataFrame(); msinv_has_lines = False

    if msinv_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error (CINVOICES): {msinv_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    if not msinv_header_df.empty:
        msinv_total = len(msinv_header_df)
        msinv_final = int(msinv_header_df["Status"].eq(MSINV_PUSH_STATUS).sum()) if "Status" in msinv_header_df.columns else 0
        msinv_other = msinv_total - msinv_final
        msinv_amt   = msinv_header_df["Grand Total"].sum() if "Grand Total" in msinv_header_df.columns else 0
        msinv_amt_f = (msinv_header_df[msinv_header_df["Status"] == MSINV_PUSH_STATUS]["Grand Total"].sum()
                       if "Grand Total" in msinv_header_df.columns and "Status" in msinv_header_df.columns else 0)
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Multi Shipment Invoices</div><div class="kpi-count">{msinv_total}</div><div class="kpi-amount">{fmt_inr(msinv_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">✅ Final — Ready to Push</div><div class="kpi-count">{msinv_final}</div><div class="kpi-amount">{fmt_inr(msinv_amt_f)}</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">⏳ Other Statuses</div><div class="kpi-count">{msinv_other}</div><div class="kpi-amount">Not pushed</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📦 Tally Registry</div><div class="kpi-count">{len(tally_msinv_nos)}</div><div class="kpi-amount">Sales vouchers in Tally</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span>🟡 <b style="color:#e3b341">Final</b> → Tally <b>Sales Invoice</b> (ISINVOICE=Yes)</span>
            <span>⚙ Header: CINVOICES &nbsp;|&nbsp; Lines: CINVOICEITEMS</span>
            <span>🚚 Shipment No. (DOCCODE) → Delivery Note No(s.) in Tally Dispatch Details</span>
            <span>💰 Party ledger: Sundry Debtors &nbsp;|&nbsp; Sales ledger: Sales Account</span>
        </div>""", unsafe_allow_html=True)

    msinv_tab1, msinv_tab2, msinv_tab3 = st.tabs([
        f"🧾 Multi Shipment Invoices ({len(msinv_merged_df) if not msinv_merged_df.empty else 0})",
        "🔍 Integrity Validation Grid",
        f"🚀 Tally Sync ({msinv_final if not msinv_header_df.empty else 0} Final)",
    ])

    # ── TAB 1: Invoice List ───────────────────────────────────────────────────
    with msinv_tab1:
        st.markdown('<p class="sec">Multi Shipment Invoices — CINVOICES</p>', unsafe_allow_html=True)

        ms_f1, ms_f2, ms_f3 = st.columns([2, 2, 4])
        with ms_f1:
            _msinv_statuses = ["All"] + (sorted(msinv_header_df["Status"].dropna().unique().tolist())
                                         if "Status" in msinv_header_df.columns else [])
            ms_sel_status = st.selectbox("Status:", _msinv_statuses, key="msinv_status")
        with ms_f2:
            _msinv_custs = ["All"] + (sorted(msinv_header_df["Customer Name"].dropna().unique().tolist())
                                      if "Customer Name" in msinv_header_df.columns else [])
            ms_sel_cust = st.selectbox("Customer:", _msinv_custs, key="msinv_cust")
        with ms_f3:
            ms_search = st.text_input("Search Invoice No. / Customer:", placeholder="e.g. SI26R01000005", key="msinv_search")

        ms_d1, ms_d2, ms_d3 = st.columns([2, 2, 4])
        with ms_d1:
            _ms_today = datetime.today().date()
            ms_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], key="msinv_date")
        ms_date_from = ms_date_to = None
        if ms_date_preset == "Today":
            ms_date_from = ms_date_to = _ms_today
        elif ms_date_preset == "Yesterday":
            from datetime import timedelta
            ms_date_from = ms_date_to = _ms_today - timedelta(days=1)
        elif ms_date_preset == "Last 7 Days":
            from datetime import timedelta
            ms_date_from = _ms_today - timedelta(days=6); ms_date_to = _ms_today
        elif ms_date_preset == "This Month":
            ms_date_from = _ms_today.replace(day=1); ms_date_to = _ms_today
        elif ms_date_preset == "Custom Range":
            with ms_d2:
                ms_date_from = st.date_input("From:", value=_ms_today.replace(day=1), key="msinv_dfrom")
            with ms_d3:
                ms_date_to   = st.date_input("To:", value=_ms_today, key="msinv_dto")

        ms_filt = msinv_merged_df.copy() if not msinv_merged_df.empty else pd.DataFrame()
        if not ms_filt.empty:
            if ms_sel_status != "All" and "Status" in ms_filt.columns:
                ms_filt = ms_filt[ms_filt["Status"] == ms_sel_status]
            if ms_sel_cust != "All" and "Customer Name" in ms_filt.columns:
                ms_filt = ms_filt[ms_filt["Customer Name"] == ms_sel_cust]
            if ms_search.strip() and "Invoice No." in ms_filt.columns:
                ms_filt = ms_filt[ms_filt["Invoice No."].astype(str).str.contains(ms_search.strip(), case=False, na=False)]
            if (ms_date_from or ms_date_to) and "Date" in ms_filt.columns:
                _ms_dates = pd.to_datetime(ms_filt["Date"], format="%d %b %Y", errors="coerce").dt.date
                if ms_date_from: ms_filt = ms_filt[_ms_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= ms_date_from)]
                if ms_date_to:   ms_filt = ms_filt[_ms_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= ms_date_to)]

            _msinv_tab1_inv_nos = set(ms_filt["Invoice No."].astype(str).tolist()) if "Invoice No." in ms_filt.columns else set()
            msinv_pipeline_raw = [r for r in msinv_raw if str(r.get("IVNUM", "")).strip() in _msinv_tab1_inv_nos]
            st.session_state["msinv_pipeline_raw"] = msinv_pipeline_raw

            ms_filt = ms_filt.copy()
            ms_filt["Tally Match"] = ms_filt["Invoice No."].apply(
                lambda x: "⚠️ Already in Tally" if str(x).strip() in tally_msinv_nos else "🆕 Safe to Push"
            )
            ms_cols = ["Status", "Tally Match", "Invoice No.", "Date", "Customer No.", "Customer Name",
                       "Grand Total", "GST", "Order Number", "Line Count", "Parts"]
            st.dataframe(
                fmt_cur(ms_filt[[c for c in ms_cols if c in ms_filt.columns]], "Grand Total", "GST"),
                use_container_width=True, height=480, hide_index=True,
            )
            st.caption(f"ℹ️ {len(ms_filt)} invoice(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")

            if msinv_has_lines and not msinv_lines_df.empty:
                with st.expander("🔎 Line Items Drill-down (with Shipment Mapping)"):
                    inv_opts = ms_filt["Invoice No."].dropna().astype(str).unique().tolist() if "Invoice No." in ms_filt.columns else []
                    if inv_opts:
                        picked = st.selectbox("Select Invoice:", inv_opts, key="msinv_drill")
                        drill_lines = msinv_lines_df[msinv_lines_df["Invoice No."].astype(str) == picked]
                        if drill_lines.empty:
                            st.caption("No line items found.")
                        else:
                            lcols = [c for c in ["Part Number", "Part Description", "Shipment No.",
                                                  "Quantity", "Unit", "Unit Price", "Discount %",
                                                  "Total Price", "Line GST", "Warehouse"] if c in drill_lines.columns]
                            st.dataframe(fmt_cur(drill_lines[lcols], "Unit Price", "Total Price", "Line GST"),
                                         use_container_width=True, height=260, hide_index=True)
                            # Show Shipment → Items summary
                            if "Shipment No." in drill_lines.columns:
                                st.markdown("**Shipment → Items mapping:**")
                                for sh, grp in drill_lines.groupby("Shipment No.", dropna=False):
                                    items_list = ", ".join(grp["Part Description"].dropna().astype(str).tolist())
                                    st.markdown(f"• `{sh}` → {items_list}")
        else:
            st.markdown('<div class="alert alert-warn">⚠ No Multi Shipment Invoices returned from Priority ERP.</div>', unsafe_allow_html=True)

    # ── TAB 2: Integrity Validation ───────────────────────────────────────────
    with msinv_tab2:
        st.markdown('<p class="sec">Integrity Validation — CINVOICES vs Tally</p>', unsafe_allow_html=True)
        _msinv_pipe = st.session_state.get("msinv_pipeline_raw", None)
        if _msinv_pipe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Multi Shipment Invoices</b> tab first to apply filters — then come back here.</div>', unsafe_allow_html=True)
        elif not _msinv_pipe:
            st.markdown('<div class="alert alert-warn">⚠ No invoices match the current filters in the Multi Shipment Invoices tab.</div>', unsafe_allow_html=True)
        else:
            ms_matrix = []
            _msinv_safe_nos = set()
            for rec in _msinv_pipe:
                inv_ref  = rec.get("IVNUM", "")
                stat_ref = str(rec.get("STATDES") or "").strip()
                customer = str(rec.get("CDES") or "").strip()
                raw_dt   = rec.get("IVDATE", "") or rec.get("CURDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount   = fmt_inr(rec.get("TOTPRICE") or 0)
                in_tally = inv_ref in tally_msinv_nos

                # Collect shipment numbers from lines
                _lines = rec.get(MSINV_SUBFORM) or []
                _sh_nos = list(dict.fromkeys(
                    str(l.get("DOCNO") or l.get("DOCCODE") or "").strip()
                    for l in _lines if (l.get("DOCNO") or l.get("DOCCODE"))
                ))
                shipments_str = ", ".join(_sh_nos) if _sh_nos else "—"

                lines_ok   = len(_lines) > 0
                shipmt_ok  = len(_sh_nos) > 0
                verdict    = ("❌ Duplicate — Already in Tally" if in_tally
                              else ("✅ Safe to Push (Final)" if stat_ref == MSINV_PUSH_STATUS
                                    else f"🚫 Not Eligible ({stat_ref})"))
                if "Safe to Push" in verdict:
                    _msinv_safe_nos.add(inv_ref)

                ms_matrix.append({
                    "Invoice No.":       inv_ref,
                    "Customer":          customer,
                    "Date":              date_str,
                    "Status":            stat_ref,
                    "Amount":            amount,
                    "Lines":             f"{'✅' if lines_ok else '❌'} {len(_lines)} line(s)",
                    "Shipment(s)":       shipments_str,
                    "Shipment Count":    len(_sh_nos),
                    "In Tally":          "⚠️ Yes" if in_tally else "🆕 No",
                    "Verdict":           verdict,
                })
            st.session_state["msinv_safe_inv_nos"] = _msinv_safe_nos

            ms_matrix_df = pd.DataFrame(ms_matrix)
            verdict_colors = {
                "✅ Safe to Push (Final)": "background-color:#0d3321;color:#3fb950",
                "❌ Duplicate — Already in Tally": "background-color:#3d1f1f;color:#f85149",
            }
            def _ms_color(val):
                return verdict_colors.get(val, "")
            if not ms_matrix_df.empty:
                st.dataframe(
                    ms_matrix_df.style.applymap(_ms_color, subset=["Verdict"]),
                    use_container_width=True, height=420, hide_index=True,
                )
                safe_n = sum(1 for r in ms_matrix if "Safe to Push" in r["Verdict"])
                dup_n  = sum(1 for r in ms_matrix if "Duplicate" in r["Verdict"])
                st.markdown(f"""
                <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;">
                    <span style="color:#3fb950">✅ {safe_n} ready to push</span>
                    <span style="color:#f85149">❌ {dup_n} already in Tally</span>
                    <span style="color:#58a6ff">🚚 Shipment column shows Priority DOCCODE values → Delivery Note No(s.) in Tally</span>
                </div>""", unsafe_allow_html=True)

    # ── TAB 3: Tally Sync ─────────────────────────────────────────────────────
    with msinv_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Final Shipment Invoices as Sales Invoices</p>', unsafe_allow_html=True)
        st.markdown(
            'Only <b>Final</b> CINVOICES are pushed as <b>Sales Invoice</b> vouchers (ISINVOICE=Yes).<br>'
            'Each item is linked to its Shipment (DOCCODE) via <code>TRACKINGNUMBER</code>.<br>'
            'All distinct Shipment numbers appear in Tally\'s <b>Delivery Note No(s.)</b> field under Dispatch Details.',
            unsafe_allow_html=True
        )

        _msinv_safe = st.session_state.get("msinv_safe_inv_nos", None)
        if _msinv_safe is None:
            st.markdown('<div class="alert alert-warn">⚠ Visit the <b>Integrity Validation</b> tab first.</div>', unsafe_allow_html=True)
            st.stop()

        # Apply same filters as Tab 1
        msinv_pool = [
            r for r in (st.session_state.get("msinv_pipeline_raw") or [])
            if str(r.get("STATDES", "")).strip() == MSINV_PUSH_STATUS
            and str(r.get("IVNUM", "")).strip() in _msinv_safe
            and str(r.get("IVNUM", "")).strip() not in tally_msinv_nos
        ]

        if ms_date_from or ms_date_to:
            def _ms_rec_date(r):
                try:
                    ts = pd.to_datetime(str(r.get("IVDATE") or r.get("CURDATE") or ""), errors="coerce")
                    return None if pd.isnull(ts) else ts.date()
                except Exception:
                    return None
            msinv_pool = [r for r in msinv_pool if (lambda d: d is not None and
                          (not ms_date_from or d >= ms_date_from) and
                          (not ms_date_to   or d <= ms_date_to))(_ms_rec_date(r))]

        st.markdown('<div class="alert alert-info">ℹ️ Only invoices that passed the <b>Integrity Validation</b> step are shown here.</div>', unsafe_allow_html=True)

        msinv_hide_dup = st.checkbox("Hide invoices already in Tally", value=True, key="msinv_hide_dup")
        if msinv_hide_dup:
            msinv_pool = [r for r in msinv_pool if str(r.get("IVNUM", "")).strip() not in tally_msinv_nos]

        st.caption(f"**{len(msinv_pool)}** Final Multi Shipment Invoice(s) in queue.")

        if not msinv_pool:
            st.markdown('<div class="alert alert-success">✅ All Final Multi Shipment Invoices are already in Tally — nothing to push.</div>', unsafe_allow_html=True)
        else:
            selected_msinv = []
            for rec in msinv_pool:
                inv_id   = rec.get("IVNUM", "?")
                cust_lbl = rec.get("CDES", "")
                val_lbl  = fmt_inr(rec.get("TOTPRICE") or 0)
                _lines   = rec.get(MSINV_SUBFORM) or []
                n_lines  = len(_lines)
                _sh_nos_disp = list(dict.fromkeys(
                    str(l.get("DOCNO") or l.get("DOCCODE") or "").strip() for l in _lines if (l.get("DOCNO") or l.get("DOCCODE"))
                ))
                sh_label = f"{len(_sh_nos_disp)} shipment(s): {', '.join(_sh_nos_disp)}" if _sh_nos_disp else "no shipments"
                is_dup   = inv_id in tally_msinv_nos
                warn     = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(
                    f"**{inv_id}** — {cust_lbl} — {val_lbl} — {n_lines} line(s) — {sh_label}{warn}",
                    value=not is_dup, key=f"msinv_chk_{inv_id}",
                ):
                    selected_msinv.append(rec)

            st.markdown("---")
            msinv_dry = st.checkbox("Dry run (preview only)", value=False, key="msinv_dry")
            if st.button(
                f"{'🧪 Dry Run' if msinv_dry else '🚀 Push'} {len(selected_msinv)} Multi Shipment Invoice(s) to Tally",
                key="msinv_push_btn",
            ):
                if not selected_msinv:
                    st.warning("No invoices selected.")
                else:
                    msinv_results = run_msinv_push(selected_msinv, msinv_dry, "MSINV-Final")
                    ok_n  = sum(1 for r in msinv_results if "✅" in str(r.get("Result", "")))
                    err_n = sum(1 for r in msinv_results if "❌" in str(r.get("Result", "")))
                    if "push_log" not in st.session_state:
                        st.session_state.push_log = []
                    st.session_state.push_log.extend(msinv_results)
                    st.session_state["msinv_last_push_results"] = msinv_results
                    st.session_state["msinv_last_push_dry"]     = msinv_dry
                    st.session_state["msinv_last_push_ok"]      = ok_n
                    st.session_state["msinv_last_push_err"]     = err_n
                    if ok_n and not msinv_dry:
                        pushed_nos = {str(r.get("Invoice No", "")).strip() for r in msinv_results if "✅" in str(r.get("Result", ""))}
                        _existing  = st.session_state.get("msinv_tally_nos_override", set())
                        st.session_state["msinv_tally_nos_override"] = _existing | pushed_nos
                        for _k in ["msinv_safe_inv_nos", "msinv_pipeline_raw"]:
                            st.session_state.pop(_k, None)
                        st.cache_data.clear()
                        st.rerun()

            with st.expander("🔬 Preview XML for selected invoices"):
                for rec in selected_msinv[:3]:
                    inv_id = rec.get("IVNUM", "?")
                    xml_preview = build_msinv_xml(rec)
                    st.markdown(f"**{inv_id}** — {rec.get('CDES', '')}")
                    st.code(xml_preview, language="xml")

        # ── Display last push results ─────────────────────────────────────────
        _lpr = st.session_state.get("msinv_last_push_results")
        if _lpr:
            _dry  = st.session_state.get("msinv_last_push_dry",  False)
            _ok   = st.session_state.get("msinv_last_push_ok",   0)
            _err  = st.session_state.get("msinv_last_push_err",  0)
            st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
            df_res = pd.DataFrame(_lpr)
            res_cols = ["Invoice No", "Customer", "Amount", "Status", "Tally Type", "Result", "Timestamp"]
            st.dataframe(df_res[[c for c in res_cols if c in df_res.columns]], use_container_width=True, hide_index=True)
            if _dry:
                st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
            elif _ok:
                st.markdown(f'<div class="alert alert-success">✅ {_ok} Sales Invoice(s) created in Tally from Multi Shipment. {_err} error(s).</div>', unsafe_allow_html=True)
            if _err and not _dry:
                st.markdown(
                    f'<div class="alert alert-error">❌ {_err} failed — verify:<br>'
                    f'• Tally Gateway active on port 9000<br>'
                    f'• "Sales" voucher type exists in Tally<br>'
                    f'• Ledger <code>{LEDGER_SALES}</code> exists under Sales Accounts<br>'
                    f'• Customer ledger exists under Sundry Debtors</div>',
                    unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  MODULE: SHIPPING DOCUMENTS  (DOCUMENTS_D → Tally Delivery Note)
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Shipping Documents Module":

    with st.spinner("Fetching Shipping Documents from Priority ERP (DOCUMENTS_D)…"):
        sh_tally_registry = query_daybook_by_type("Delivery Note") | st.session_state.get("sh_tally_nos_override", set())
        try:
            sh_raw, sh_expected_count, sh_active_expand, sh_resolved_so_subform = fetch_live_sh_data()
            sh_header_df = build_sh_header_df(sh_raw, sh_active_expand, sh_resolved_so_subform) if sh_raw else pd.DataFrame()
            sh_lines_df  = build_sh_lines_df(sh_raw, sh_active_expand) if sh_raw else pd.DataFrame()
            if sh_active_expand and not str(sh_active_expand).startswith("(none"):
                SH_ITEMS_SUBFORM = sh_active_expand
            if sh_resolved_so_subform:
                SH_SO_SUBFORM = sh_resolved_so_subform
            sh_fetch_err = None
        except Exception as e:
            sh_fetch_err = str(e); sh_raw = []; sh_header_df = pd.DataFrame()
            sh_lines_df = pd.DataFrame(); sh_expected_count = None
            sh_active_expand = "(none)"; sh_resolved_so_subform = None

    if sh_fetch_err:
        st.markdown(f'<div class="alert alert-warn">Priority API Error (DOCUMENTS_D): {sh_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    sh_tot_count = len(sh_header_df) if not sh_header_df.empty else 0
    sh_final_cnt = int(sh_header_df["Status"].fillna("").str.strip().str.upper().eq(SH_STATUS_GATE.upper()).sum()) if not sh_header_df.empty and "Status" in sh_header_df.columns else 0
    sh_sync_cnt  = (sum(1 for n in sh_header_df["Doc. Number"].astype(str).unique() if str(n).strip() in sh_tally_registry) if not sh_header_df.empty and "Doc. Number" in sh_header_df.columns else 0)
    sh_pend_cnt  = max(0, sh_final_cnt - sh_sync_cnt)
    sh_err_cnt   = sum(1 for r in st.session_state.get("sh_last_push_results", []) if any(w in r.get("Result", "") for w in ("Error", "Fault", "fault")))

    if not sh_header_df.empty:
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Records</div><div class="kpi-count">{sh_tot_count}</div><div class="kpi-amount">Active OData Entries</div></div>
            <div class="kpi kpi-auth"><div class="kpi-label">Eligible (Final)</div><div class="kpi-count">{sh_final_cnt}</div><div class="kpi-amount">Status = Final</div></div>
            <div class="kpi kpi-final"><div class="kpi-label">Synced</div><div class="kpi-count">{sh_sync_cnt}</div><div class="kpi-amount">Delivery Notes in Tally</div></div>
            <div class="kpi kpi-confirmed"><div class="kpi-label">Pending</div><div class="kpi-count">{sh_pend_cnt}</div><div class="kpi-amount">Awaiting Transport Run</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">Errors</div><div class="kpi-count">{sh_err_cnt}</div><div class="kpi-amount">Runtime Pipeline Faults</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span><b style="color:#e3b341">Final</b> to Tally <b>Delivery Note</b> (ISINVOICE=No)</span>
            <span>Header: DOCUMENTS_D | Lines: {sh_active_expand}</span>
            <span>SO Subform: <code>{sh_resolved_so_subform or "line/header fallback"}</code></span>
            <span>Party ledger: Sundry Debtors | Sales ledger: Sales Account</span>
        </div>""", unsafe_allow_html=True)

    sh_tab1, sh_tab2, sh_tab3 = st.tabs([
        f"📋 Customer Shipments — DOCUMENTS_D ({sh_tot_count})",
        "🔍 Integrity Validation Grid",
        f"🚀 Tally Sync ({sh_pend_cnt} Staged)",
    ])

    # ── TAB 1: Shipment list ──────────────────────────────────────────────────
    with sh_tab1:
        st.markdown('<p class="sec">Customer Shipments — DOCUMENTS_D</p>', unsafe_allow_html=True)

        sh_f1, sh_f2, sh_f3 = st.columns([2, 2, 4])
        with sh_f1:
            sh_sel_status = st.selectbox("Status Filter:", ["All", "Draft", "Final", "Canceled"], key="sh_filter_status")
        with sh_f2:
            _sh_custs = (["All"] + sorted(sh_header_df["Customer Name"].dropna().unique().tolist())
                         if "Customer Name" in sh_header_df.columns else ["All"])
            sh_sel_cust = st.selectbox("Filter Customer Account:", _sh_custs, key="sh_filter_cust")
        with sh_f3:
            sh_search_str = st.text_input("Search Shipment Doc. / SO Reference:",
                                          placeholder="e.g. SH26R01", key="sh_search_field")

        sh_d1, sh_d2, sh_d3 = st.columns([2, 2, 4])
        _sh_today = datetime.today().date()
        with sh_d1:
            sh_date_preset = st.selectbox("Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"], index=0, key="sh_date_preset")
        sh_date_from = sh_date_to = None
        if sh_date_preset == "Today":
            sh_date_from = sh_date_to = _sh_today
        elif sh_date_preset == "Yesterday":
            sh_date_from = sh_date_to = _sh_today - timedelta(days=1)
        elif sh_date_preset == "Last 7 Days":
            sh_date_from = _sh_today - timedelta(days=6); sh_date_to = _sh_today
        elif sh_date_preset == "This Month":
            sh_date_from = _sh_today.replace(day=1); sh_date_to = _sh_today
        elif sh_date_preset == "Custom Range":
            with sh_d2:
                sh_date_from = st.date_input("From:", value=_sh_today.replace(day=1), key="sh_df_node")
            with sh_d3:
                sh_date_to   = st.date_input("To:", value=_sh_today, key="sh_dt_node")
        else:
            with sh_d2:
                st.caption("Showing all dates.")

        sh_filt_df = sh_header_df.copy() if not sh_header_df.empty else pd.DataFrame()

        if not sh_filt_df.empty:
            if sh_sel_status != "All" and "Status" in sh_filt_df.columns:
                sh_filt_df = sh_filt_df[sh_filt_df["Status"] == sh_sel_status]
            if sh_sel_cust != "All" and "Customer Name" in sh_filt_df.columns:
                sh_filt_df = sh_filt_df[sh_filt_df["Customer Name"] == sh_sel_cust]
            if sh_search_str.strip() and "Doc. Number" in sh_filt_df.columns:
                _s = sh_search_str.strip()
                _sh_mask = sh_filt_df["Doc. Number"].astype(str).str.contains(_s, case=False, na=False)
                if "Sales Order" in sh_filt_df.columns:
                    _sh_mask |= sh_filt_df["Sales Order"].astype(str).str.contains(_s, case=False, na=False)
                sh_filt_df = sh_filt_df[_sh_mask]
            if (sh_date_from or sh_date_to) and "Date" in sh_filt_df.columns:
                _sh_dates = pd.to_datetime(sh_filt_df["Date"], errors="coerce", dayfirst=True).dt.date
                _sh_valid = _sh_dates.notna()
                if sh_date_from:
                    sh_filt_df = sh_filt_df[_sh_valid & (_sh_dates >= sh_date_from)]
                if sh_date_to:
                    sh_filt_df = sh_filt_df[_sh_valid & (_sh_dates <= sh_date_to)]

        # Always write pipeline — even if empty after filters
        _sh_active_nos = (
            set(sh_filt_df["Doc. Number"].apply(_sh_doc_key).tolist())
            if not sh_filt_df.empty and "Doc. Number" in sh_filt_df.columns else set()
        )
        st.session_state["sh_pipeline_raw"] = [
            r for r in sh_raw if _sh_doc_key(r.get("DOCNO")) in _sh_active_nos
        ]

        if not sh_filt_df.empty:
            sh_filt_df = sh_filt_df.copy()
            sh_filt_df["Tally Match"] = sh_filt_df["Doc. Number"].apply(
                lambda x: "⚠️ Already in Tally" if _sh_doc_key(x) in sh_tally_registry else "🆕 Safe to Push"
            )
            sh_display_cols = [
                "Status", "Tally Match", "Doc. Number", "Date",
                "Customer No.", "Customer Name", "Sales Order",
                "Total Before Discount", "VAT", "Final Price", "Qty of Items",
                "Lorry No.", "Tracking Number", "VAT Code",
            ]
            st.dataframe(
                fmt_cur(sh_filt_df[[c for c in sh_display_cols if c in sh_filt_df.columns]],
                        "Total Before Discount", "VAT", "Final Price"),
                use_container_width=True, height=480, hide_index=True,
            )
            st.caption(f"ℹ️ {len(sh_filt_df)} shipment(s) shown — these flow into the Integrity Validation and Tally Sync tabs.")
        else:
            st.markdown('<div class="alert alert-warn">⚠ No Customer Shipments match the current filters.</div>', unsafe_allow_html=True)

    # ── TAB 2: Integrity Validation ───────────────────────────────────────────
    with sh_tab2:
        st.markdown('<p class="sec">Integrity Validation — Priority vs Tally</p>', unsafe_allow_html=True)
        _sh_pipe2 = st.session_state.get("sh_pipeline_raw") or sh_raw

        if not _sh_pipe2:
            st.markdown('<div class="alert alert-warn">⚠ No shipments loaded from Priority ERP.</div>', unsafe_allow_html=True)
        else:
            sh_matrix = []
            _sh_safe_nos = set()
            _sh_expand_key = sh_active_expand if sh_active_expand and not str(sh_active_expand).startswith("(none") else SH_ITEMS_SUBFORM
            for rec in _sh_pipe2:
                doc_no   = rec.get("DOCNO", "")
                status   = str(rec.get("STATDES", "")).strip()
                customer = str(rec.get("CDES", "")).strip()
                raw_dt   = rec.get("DOCDATE", "")
                try:
                    ts = pd.to_datetime(str(raw_dt), errors="coerce")
                    date_str = ts.strftime("%d %b %Y") if not pd.isnull(ts) else ""
                except Exception:
                    date_str = ""
                amount  = fmt_inr(rec.get("TOTPRICE", 0))
                in_tally = _sh_doc_key(doc_no) in sh_tally_registry

                sh_so_refs_v = _collect_so_refs(rec, sh_resolved_so_subform)
                sh_so_ref    = ", ".join(sh_so_refs_v) if sh_so_refs_v else ""

                sub_lines  = rec.get(_sh_expand_key, []) or []
                slab_items = []
                for line in sub_lines:
                    pn       = line.get("PARTNAME", "")
                    raw_rate = line.get("MAHI_TAXRATE")
                    rate_pct = float(raw_rate) if raw_rate else _sh_taxcode_to_rate(line.get("RBS_TAXCODE"))
                    slab_items.append(f"{pn} ({rate_pct:g}%)")
                slab_string = " | ".join(slab_items) if slab_items else "—"

                if in_tally:
                    sh_verdict = "❌ Duplicate — Already in Tally"
                elif status.upper() == SH_STATUS_GATE.upper():
                    sh_verdict = "✅ Safe to Push (Final)"
                    _sh_safe_nos.add(doc_no)
                else:
                    sh_verdict = f"🚫 Not Eligible ({status})"

                sh_matrix.append({
                    "Verdict":              sh_verdict,
                    "Shipment Doc ID":      doc_no,
                    "Date":                 date_str,
                    "Customer":             customer,
                    "Amount":               amount,
                    "SO Reference(s)":      sh_so_ref,
                    "Item-wise Tax Slabs":  slab_string,
                    "Status":               status,
                    "Tally Books Link":     "Found" if in_tally else "Absent",
                })

            st.session_state["sh_safe_doc_nos"] = _sh_safe_nos
            st.dataframe(pd.DataFrame(sh_matrix), use_container_width=True, hide_index=True)
            safe_n = len(_sh_safe_nos)
            dup_n  = sum(1 for r in sh_matrix if "Duplicate" in r["Verdict"])
            skip_n = sum(1 for r in sh_matrix if "Not Eligible" in r["Verdict"])
            st.caption(f"✅ {safe_n} safe to push · ❌ {dup_n} duplicate(s) · 🚫 {skip_n} ineligible")

    # ── TAB 3: Tally Sync ─────────────────────────────────────────────────────
    with sh_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Shipping Documents as Delivery Notes</p>', unsafe_allow_html=True)

        # Build sync pool from the Tab 1 filtered pipeline (respects date/status filters).
        # Falls back to full sh_raw only if pipeline hasn't been set yet.
        _sh_pipe3 = st.session_state.get("sh_pipeline_raw") or sh_raw
        sh_pool = [
            r for r in _sh_pipe3
            if str(r.get("STATDES", "")).strip().upper() == SH_STATUS_GATE.upper()
            and _sh_doc_key(r.get("DOCNO", "")) not in sh_tally_registry
        ]

        st.markdown('<div class="alert alert-info">ℹ️ Only Final shipments not already in Tally are shown. '
                    f'Tally Delivery Note registry: <b>{len(sh_tally_registry)}</b> voucher(s).</div>',
                    unsafe_allow_html=True)

        sh_hide_existing = st.checkbox("Hide records already in Tally", value=True, key="sh_hide_ex")
        if sh_hide_existing:
            sh_pool = [r for r in sh_pool if _sh_doc_key(r.get("DOCNO", "")) not in sh_tally_registry]

        st.caption(f"**{len(sh_pool)}** shipment(s) in queue.")

        if not sh_pool:
            st.info("No outstanding shipments to push. Either all are already in Tally, or no Final records exist.")
        else:
            selected_sh = []
            for rec in sh_pool:
                doc_id      = rec.get("DOCNO", "?")
                cust_lbl    = rec.get("CDES", "")
                val_lbl     = fmt_inr(rec.get("TOTPRICE") or 0)
                so_refs_lbl = _collect_so_refs(rec, sh_resolved_so_subform)
                so_lbl      = f" | SO: {', '.join(so_refs_lbl)}" if so_refs_lbl else ""
                lorry_lbl   = f" | Lorry: {rec.get('LORRYNO')}" if rec.get("LORRYNO") else ""
                is_dup      = _sh_doc_key(doc_id) in sh_tally_registry
                warn        = " 🔴 [DUPLICATE IN TALLY]" if is_dup else " 🟢"
                if st.checkbox(
                    f"**{doc_id}**{so_lbl}{lorry_lbl} — {cust_lbl} — {val_lbl}{warn}",
                    value=not is_dup, key=f"sh_chk_{doc_id}"
                ):
                    selected_sh.append(rec)

            st.markdown("---")
            sh_dry = st.checkbox("Dry run (preview only)", value=False, key="sh_dry")
            if st.button(
                f"{'🧪 Dry Run' if sh_dry else '🚀 Push'} {len(selected_sh)} Shipment(s) to Tally",
                key="sh_push_btn", type="primary",
            ):
                if not selected_sh:
                    st.warning("No shipments selected.")
                else:
                    sh_run_results = run_sh_push(selected_sh, sh_resolved_so_subform, sh_dry)
                    sh_ok_n  = sum(1 for r in sh_run_results if "Synchronized" in str(r.get("Result", "")))
                    sh_err_n = sum(1 for r in sh_run_results if any(w in r.get("Result", "") for w in ("Error", "Fault", "fault")))
                    st.session_state["sh_last_push_results"] = sh_run_results
                    if sh_ok_n and not sh_dry:
                        pushed_nos = {str(r.get("Doc. No", "")).strip() for r in sh_run_results if "Synchronized" in str(r.get("Result", ""))}
                        st.session_state["sh_tally_nos_override"] = st.session_state.get("sh_tally_nos_override", set()) | pushed_nos
                        for _k in ["sh_safe_doc_nos", "sh_pipeline_raw"]:
                            st.session_state.pop(_k, None)
                        st.cache_data.clear()
                        st.rerun()

        sh_last_logs = st.session_state.get("sh_last_push_results", [])
        if sh_last_logs:
            _sh_dry = any("Dry Run" in str(r.get("Result", "")) for r in sh_last_logs)
            _sh_ok  = sum(1 for r in sh_last_logs if "Synchronized" in str(r.get("Result", "")))
            _sh_err = sum(1 for r in sh_last_logs if any(w in r.get("Result", "") for w in ("Error", "Fault", "fault")))
            st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
            sh_log_df = pd.DataFrame(sh_last_logs)
            sh_res_cols = ["Doc. No", "Customer", "Amount", "Tally Type", "Result", "Timestamp"]
            st.dataframe(sh_log_df[[c for c in sh_res_cols if c in sh_log_df.columns]], use_container_width=True, hide_index=True)
            if _sh_dry:
                st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
            elif _sh_ok:
                st.markdown(f'<div class="alert alert-success">✅ {_sh_ok} Delivery Note(s) created in Tally. {_sh_err} error(s).</div>', unsafe_allow_html=True)
            if _sh_err and not _sh_dry:
                st.markdown(
                    f'<div class="alert alert-warn">❌ {_sh_err} failed — verify:<br>'
                    f'• Tally Gateway active on port 9000<br>'
                    f'• "Delivery Note" voucher type exists in Tally<br>'
                    f'• Customer ledger exists under Sundry Debtors<br>'
                    f'• Ledger <code>{LEDGER_SALES}</code> exists under Sales Accounts</div>',
                    unsafe_allow_html=True)
            with st.expander("🔬 View Compiled XML Blocks"):
                for entry in sh_last_logs:
                    st.markdown(f"**Doc:** `{entry['Doc. No']}`")
                    diag = entry.get("Diagnostics", {})
                    if diag:
                        diag_cols  = st.columns(2)
                        diag_items = list(diag.items())
                        for i, (k, v) in enumerate(diag_items):
                            diag_cols[i % 2].caption(f"`{k}`: **{v}**")
                    st.code(entry["XML"], language="xml")


# ═══════════════════════════════════════════════════════════════════════════════
#  BULK SYNC MODULE — Fetch & push multiple modules in one pass
#  All existing module functions are reused as-is; nothing is duplicated.
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Bulk Sync Module":

    # ── Module config table ──────────────────────────────────────────────────
    # Each entry describes one module: label, fetch fn, header/lines/merged builders,
    # push fn, eligible status set, record-ID field, Tally voucher type for dup check,
    # and display fields for Tab 1 grid and Tab 3 queue.
    BULK_MODULES = [
        {
            "key":          "po",
            "label":        "📦 Purchase Orders",
            "fetch":        fetch_orders,
            "build_header": build_header_df,
            "build_lines":  build_lines_df,
            "build_merged": build_merged_df,
            "run_push":     run_po_push,
            "push_statuses": ELIGIBLE_STATUSES,
            "rec_id_field": "ORDNAME",
            "tally_vch":    "Purchase Order",
            "amount_field": "MAINDISPRICE",
            "party_field":  "CDES",
            "display_cols": ["Order", "Date", "Vendor Name", "Total Cost (INR)", "Status"],
        },
        {
            "key":          "grv",
            "label":        "🚚 Goods Receiving Vouchers",
            "fetch":        fetch_grv,
            "build_header": build_grv_header_df,
            "build_lines":  build_grv_lines_df,
            "build_merged": build_grv_merged_df,
            "run_push":     run_grv_push,
            "push_statuses": GRV_PUSH_STATUSES,
            "rec_id_field": "DOCNO",
            "tally_vch":    "Receipt Note",
            "amount_field": "TOTPRICE",
            "party_field":  "CDES",
            "display_cols": ["GRV No.", "Date", "Vendor Name", "Total Amount", "Status"],
        },
        {
            "key":          "mgrv",
            "label":        "🧾 Multi GRV Invoices",
            "fetch":        fetch_mgrv_invoices,
            "build_header": build_mgrv_header_df,
            "build_lines":  build_mgrv_lines_df,
            "build_merged": build_mgrv_merged_df,
            "run_push":     run_mgrv_push,
            "push_statuses": MGRV_PUSH_STATUSES,
            "rec_id_field": "IVNUM",
            "tally_vch":    "Purchase",
            "amount_field": "TOTPRICE",
            "party_field":  "SUPDES",
            "display_cols": ["Internal No.", "Date", "Vendor Name", "Amount Owing", "Status"],
        },
        {
            "key":          "so",
            "label":        "🛒 Sales Orders",
            "fetch":        fetch_sales_orders,
            "build_header": build_so_header_df,
            "build_lines":  build_so_lines_df,
            "build_merged": build_so_merged_df,
            "run_push":     run_so_push,
            "push_statuses": SO_PUSH_STATUSES,
            "rec_id_field": "ORDNAME",
            "tally_vch":    "Sales Order",
            "amount_field": "TOTPRICE",
            "party_field":  "CDES",
            "display_cols": ["Order No.", "DATE", "Cust. Name", "Final Price", "Status"],
        },
        {
            "key":          "sinv",
            "label":        "🧾 Sales Invoices",
            "fetch":        fetch_sales_invoices,
            "build_header": build_sinv_header_df,
            "build_lines":  build_sinv_lines_df,
            "build_merged": build_sinv_merged_df,
            "run_push":     run_sinv_push,
            "push_statuses": {SINV_PUSH_STATUS},
            "rec_id_field": "IVNUM",
            "tally_vch":    "Sales",
            "amount_field": "TOTPRICE",
            "party_field":  "CDES",
            "display_cols": ["Invoice No.", "Date", "Customer Name", "Grand Total", "Status"],
        },
        {
            "key":          "otc",
            "label":        "🏪 OTC Sales Invoices",
            "fetch":        fetch_otc_sales_invoices,
            "build_header": build_otc_header_df,
            "build_lines":  build_otc_lines_df,
            "build_merged": build_otc_merged_df,
            "run_push":     run_otc_push,
            "push_statuses": {"Final"},
            "rec_id_field": "IVNUM",
            "tally_vch":    OTC_TALLY_VCH_TYPE,
            "amount_field": "TOTPRICE",
            "party_field":  "CDES",
            "display_cols": ["Invoice No.", "Date", "Customer Name", "Grand Total", "Status"],
        },
        {
            "key":          "msinv",
            "label":        "🚀 Multi Shipment Invoices",
            "fetch":        fetch_msinv_invoices,
            "build_header": build_msinv_header_df,
            "build_lines":  build_msinv_lines_df,
            "build_merged": build_msinv_merged_df,
            "run_push":     run_msinv_push,
            "push_statuses": MSINV_PUSH_STATUSES,
            "rec_id_field": "IVNUM",
            "tally_vch":    "Sales",
            "amount_field": "TOTPRICE",
            "party_field":  "CDES",
            "display_cols": ["Invoice No.", "Date", "Customer Name", "Grand Total", "Status"],
        },
    ]

    st.markdown('<p class="sec">⚡ Bulk Sync — Select Modules to Fetch & Push</p>', unsafe_allow_html=True)
    st.markdown(
        '<div class="alert alert-info">Select one or more modules below. '
        'Tab 1 fetches all selected modules in one pass. '
        'Tab 3 lets you choose records per module and push everything with a single button.</div>',
        unsafe_allow_html=True
    )

    # ── Module selector (checkboxes in a compact 2-col grid) ─────────────────
    st.markdown("**Choose modules to include:**")
    _bulk_cols = st.columns(4)
    bulk_selected_keys = []
    for _bi, _bm in enumerate(BULK_MODULES):
        with _bulk_cols[_bi % 4]:
            _default = st.session_state.get(f"bulk_chk_{_bm['key']}", False)
            if st.checkbox(_bm["label"], value=_default, key=f"bulk_chk_{_bm['key']}"):
                bulk_selected_keys.append(_bm["key"])

    bulk_selected = [m for m in BULK_MODULES if m["key"] in bulk_selected_keys]

    if not bulk_selected:
        st.info("☝️ Select at least one module above to get started.")
        st.stop()

    # ── 3 tabs ───────────────────────────────────────────────────────────────
    bulk_tab1, bulk_tab2, bulk_tab3 = st.tabs([
        f"📋 Data ({len(bulk_selected)} module(s))",
        "🔍 Integrity Validation",
        "🚀 Tally Sync",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — Fetch & display
    # ════════════════════════════════════════════════════════════════════════
    with bulk_tab1:
        st.markdown('<p class="sec">Fetched Records — All Selected Modules</p>', unsafe_allow_html=True)

        _bulk_date_col1, _bulk_date_col2 = st.columns([2, 6])
        with _bulk_date_col1:
            _bulk_today = datetime.today().date()
            bulk_date_preset = st.selectbox(
                "Date Filter:",
                ["Last 7 Days", "Today", "Yesterday", "This Month", "All Dates", "Custom Range"],
                key="bulk_date_preset"
            )
        bulk_date_from = bulk_date_to = None
        if bulk_date_preset == "Today":
            bulk_date_from = bulk_date_to = _bulk_today
        elif bulk_date_preset == "Yesterday":
            from datetime import timedelta
            bulk_date_from = bulk_date_to = _bulk_today - timedelta(days=1)
        elif bulk_date_preset == "Last 7 Days":
            from datetime import timedelta
            bulk_date_from = _bulk_today - timedelta(days=6); bulk_date_to = _bulk_today
        elif bulk_date_preset == "This Month":
            bulk_date_from = _bulk_today.replace(day=1); bulk_date_to = _bulk_today
        elif bulk_date_preset == "Custom Range":
            with _bulk_date_col2:
                _cr1, _cr2 = st.columns(2)
                with _cr1: bulk_date_from = st.date_input("From:", value=_bulk_today.replace(day=1), key="bulk_date_from")
                with _cr2: bulk_date_to   = st.date_input("To:",   value=_bulk_today, key="bulk_date_to")

        # Fetch all selected modules
        bulk_raw        = {}   # key -> raw list
        bulk_merged     = {}   # key -> merged_df
        bulk_fetch_errs = {}   # key -> error string

        for _bm in bulk_selected:
            _k = _bm["key"]
            with st.spinner(f"Fetching {_bm['label']}…"):
                try:
                    _raw, _ = _bm["fetch"]()
                    _hdf = _bm["build_header"](_raw) if _raw else pd.DataFrame()
                    _ldf = _bm["build_lines"](_raw)  if _raw else pd.DataFrame()
                    _mdf = _bm["build_merged"](_hdf, _ldf) if not _hdf.empty else pd.DataFrame()
                    bulk_raw[_k]    = _raw
                    bulk_merged[_k] = _mdf
                    st.session_state[f"bulk_raw_{_k}"]    = _raw
                    st.session_state[f"bulk_merged_{_k}"] = _mdf
                except Exception as _e:
                    bulk_fetch_errs[_k] = str(_e)
                    bulk_raw[_k]    = []
                    bulk_merged[_k] = pd.DataFrame()
                    st.session_state[f"bulk_raw_{_k}"]    = []
                    st.session_state[f"bulk_merged_{_k}"] = pd.DataFrame()

        if bulk_fetch_errs:
            for _k, _err in bulk_fetch_errs.items():
                st.markdown(f'<div class="alert alert-error">⚠ {_k.upper()} fetch error: {_err}</div>', unsafe_allow_html=True)

        # KPI summary row
        _kpi_parts = []
        for _bm in bulk_selected:
            _k   = _bm["key"]
            _mdf = bulk_merged.get(_k, pd.DataFrame())
            _cnt = len(_mdf) if not _mdf.empty else 0
            _pushable = 0
            if not _mdf.empty and "Status" in _mdf.columns:
                _pushable = int(_mdf["Status"].isin(_bm["push_statuses"]).sum())
            _kpi_parts.append(
                f'<div class="kpi kpi-total"><div class="kpi-label">{_bm["label"]}</div>'
                f'<div class="kpi-count">{_cnt}</div>'
                f'<div class="kpi-amount">{_pushable} pushable</div></div>'
            )
        if _kpi_parts:
            st.markdown(f'<div class="kpi-grid">{"".join(_kpi_parts)}</div>', unsafe_allow_html=True)

        # Per-module expandable data tables
        for _bm in bulk_selected:
            _k   = _bm["key"]
            _mdf = bulk_merged.get(_k, pd.DataFrame()).copy()

            # Apply date filter
            if (bulk_date_from or bulk_date_to) and not _mdf.empty:
                for _dcol in ["Date", "DATE", "CURDATE", "IVDATE"]:
                    if _dcol in _mdf.columns:
                        _dates = pd.to_datetime(_mdf[_dcol], errors="coerce").dt.date
                        if bulk_date_from: _mdf = _mdf[_dates.apply(lambda d: d is not None and not isinstance(d, float) and d >= bulk_date_from)]
                        if bulk_date_to:   _mdf = _mdf[_dates.apply(lambda d: d is not None and not isinstance(d, float) and d <= bulk_date_to)]
                        break

            _cnt = len(_mdf)
            with st.expander(f"{_bm['label']} — {_cnt} record(s)", expanded=(_cnt > 0)):
                if _mdf.empty:
                    st.info("No records found.")
                else:
                    _show_cols = [c for c in _bm["display_cols"] if c in _mdf.columns]
                    st.dataframe(_mdf[_show_cols] if _show_cols else _mdf, use_container_width=True, hide_index=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Integrity Validation Grid
    # ════════════════════════════════════════════════════════════════════════
    with bulk_tab2:
        st.markdown('<p class="sec">Integrity Validation — All Selected Modules</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">Records are checked against Tally for duplicates '
            'and filtered to only pushable statuses. Safe records are passed to Tab 3.</div>',
            unsafe_allow_html=True
        )

        bulk_safe = {}   # key -> set of safe record IDs

        for _bm in bulk_selected:
            _k        = _bm["key"]
            _raw      = st.session_state.get(f"bulk_raw_{_k}", bulk_raw.get(_k, []))
            _id_field = _bm["rec_id_field"]

            with st.spinner(f"Querying Tally for {_bm['label']} duplicates…"):
                try:
                    _tally_nos = query_daybook_by_type(_bm["tally_vch"])
                except Exception:
                    _tally_nos = set()

            _matrix = []
            _safe_ids = set()

            for _r in _raw:
                _rec_id  = str(_r.get(_id_field) or _r.get("ORDNAME") or _r.get("IVNUM") or _r.get("DOCNO") or "").strip()
                _status  = str(_r.get("STATDES") or _r.get("ORDSTATUSDES") or _r.get("Status") or "").strip()
                _party   = str(_r.get(_bm["party_field"]) or _r.get("CDES") or "").strip()
                try:
                    _amt = float(_r.get(_bm["amount_field"]) or _r.get("TOTPRICE") or 0)
                except Exception:
                    _amt = 0.0
                _in_tally = _rec_id in _tally_nos

                if _in_tally:
                    _verdict = "🔴 Duplicate in Tally"
                elif _status in _bm["push_statuses"]:
                    _verdict = f"✅ Safe to Push ({_status})"
                    _safe_ids.add(_rec_id)
                else:
                    _verdict = f"🚫 Not Eligible ({_status})"

                _matrix.append({
                    "Module":      _bm["label"],
                    "Record ID":   _rec_id,
                    "Party":       _party,
                    "Amount":      fmt_inr(_amt),
                    "Status":      _status,
                    "Tally Match": "Found" if _in_tally else "Not Found",
                    "Verdict":     _verdict,
                })

            bulk_safe[_k] = _safe_ids
            st.session_state[f"bulk_safe_{_k}"] = _safe_ids

            _safe_n = len(_safe_ids)
            _dup_n  = sum(1 for x in _matrix if "Duplicate" in x["Verdict"])
            _skip_n = sum(1 for x in _matrix if "Not Eligible" in x["Verdict"])

            with st.expander(
                f"{_bm['label']} — ✅ {_safe_n} safe · 🔴 {_dup_n} dup · 🚫 {_skip_n} skip",
                expanded=(_safe_n > 0)
            ):
                if _matrix:
                    st.dataframe(pd.DataFrame(_matrix), use_container_width=True, hide_index=True)
                else:
                    st.info("No records.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — Tally Sync (push)
    # ════════════════════════════════════════════════════════════════════════
    with bulk_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Selected Modules</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">Only records that passed Integrity Validation '
            'are shown. Use checkboxes to select which records to push.</div>',
            unsafe_allow_html=True
        )

        # Build per-module push queues
        bulk_push_selections = {}   # key -> list of selected raw records

        for _bm in bulk_selected:
            _k        = _bm["key"]
            _raw      = st.session_state.get(f"bulk_raw_{_k}", bulk_raw.get(_k, []))
            _safe_ids = st.session_state.get(f"bulk_safe_{_k}", bulk_safe.get(_k, set()))
            _id_field = _bm["rec_id_field"]

            # Fall back: compute safe IDs on-the-fly if Tab 2 was never visited
            if not _safe_ids and _raw:
                try:
                    _tally_nos = query_daybook_by_type(_bm["tally_vch"])
                except Exception:
                    _tally_nos = set()
                _safe_ids = {
                    str(_r.get(_id_field) or "").strip()
                    for _r in _raw
                    if str(_r.get("STATDES") or _r.get("ORDSTATUSDES") or "").strip() in _bm["push_statuses"]
                    and str(_r.get(_id_field) or "").strip() not in _tally_nos
                }

            _pool = [_r for _r in _raw if str(_r.get(_id_field) or "").strip() in _safe_ids]

            if not _pool:
                continue

            st.markdown(f"**{_bm['label']}** — {len(_pool)} record(s) ready")
            _selected_recs = []
            _sel_cols = st.columns(2)
            for _ri, _r in enumerate(_pool):
                _rid   = str(_r.get(_id_field) or "").strip()
                _party = str(_r.get(_bm["party_field"]) or _r.get("CDES") or "").strip()
                try:
                    _amt = fmt_inr(float(_r.get(_bm["amount_field"]) or _r.get("TOTPRICE") or 0))
                except Exception:
                    _amt = "—"
                with _sel_cols[_ri % 2]:
                    if st.checkbox(f"**{_rid}** — {_party} — {_amt} 🟢", value=True, key=f"bulk_sel_{_k}_{_rid}"):
                        _selected_recs.append(_r)

            bulk_push_selections[_k] = _selected_recs
            st.markdown("---")

        # Total selected count across all modules
        _total_selected = sum(len(v) for v in bulk_push_selections.values())

        if not bulk_push_selections:
            st.info("No pushable records found. Run Integrity Validation in Tab 2 first.")
        else:
            st.markdown(f"**{_total_selected} total record(s) selected across {len(bulk_push_selections)} module(s)**")
            _bulk_dry = st.checkbox("Dry run (preview only)", value=False, key="bulk_dry")

            if st.button(
                f"{'🧪 Dry Run' if _bulk_dry else '🚀 Push'} {_total_selected} record(s) to Tally",
                key="bulk_push_btn",
                disabled=(_total_selected == 0),
            ):
                all_results = []
                for _bm in bulk_selected:
                    _k    = _bm["key"]
                    _recs = bulk_push_selections.get(_k, [])
                    if not _recs:
                        continue
                    st.markdown(f"**Pushing {_bm['label']} ({len(_recs)} record(s))…**")
                    _res = _bm["run_push"](_recs, _bulk_dry, f"BULK-{_k.upper()}")
                    all_results.extend(_res)

                # Combined results table
                if all_results:
                    st.markdown('<p class="sec">Bulk Push Results</p>', unsafe_allow_html=True)
                    _df_res = pd.DataFrame(all_results)
                    _res_cols = ["Source", "Order No", "Invoice No", "Supplier/Customer", "Vendor", "Customer",
                                 "Amount", "Status", "Tally Type", "Result", "Timestamp"]
                    st.dataframe(
                        _df_res[[c for c in _res_cols if c in _df_res.columns]],
                        use_container_width=True, hide_index=True
                    )
                    _ok_n  = sum(1 for r in all_results if "✅" in str(r.get("Result", "")))
                    _err_n = sum(1 for r in all_results if "❌" in str(r.get("Result", "")))
                    if _bulk_dry:
                        st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div class="alert alert-success">✅ {_ok_n} voucher(s) pushed successfully. '
                            f'{_err_n} error(s).</div>',
                            unsafe_allow_html=True
                        )
                    if "push_log" not in st.session_state:
                        st.session_state.push_log = []
                    st.session_state.push_log.extend(all_results)

# ═══════════════════════════════════════════════════════════════════════════════
#  UI: ENTRY JOURNAL MODULE
# ═══════════════════════════════════════════════════════════════════════════════
elif active_module == "Entry Journal Module":

    with st.spinner("Fetching Entry Journals from Priority ERP (FNCTRANS)…"):
        jrnl_fetch_err = None
        jrnl_raw = []; jrnl_has_lines = False
        jrnl_header_df = pd.DataFrame(); jrnl_lines_df = pd.DataFrame(); jrnl_merged_df = pd.DataFrame()
        try:
            jrnl_raw, jrnl_has_lines = fetch_fnctrans()
        except Exception as e:
            jrnl_fetch_err = str(e)
        if not jrnl_fetch_err:
            try:
                jrnl_header_df = build_jrnl_header_df(jrnl_raw) if jrnl_raw else pd.DataFrame()
                jrnl_lines_df  = build_jrnl_lines_df(jrnl_raw)  if jrnl_raw else pd.DataFrame()
                jrnl_merged_df = build_jrnl_merged_df(jrnl_header_df, jrnl_lines_df, jrnl_raw) if not jrnl_header_df.empty else pd.DataFrame()
            except Exception as e:
                jrnl_fetch_err = f"Build error (data received OK) — {e}"

    if jrnl_fetch_err:
        st.markdown(f'<div class="alert alert-error">⚠ Priority API Error (FNCTRANS): {jrnl_fetch_err}</div>', unsafe_allow_html=True)
        st.stop()

    # ── KPI strip ─────────────────────────────────────────────────────────────
    if not jrnl_header_df.empty:
        jrnl_total   = len(jrnl_header_df)
        jrnl_posted  = int(jrnl_header_df["Posted"].eq(JRNL_PUSH_STATUS).sum()) if "Posted" in jrnl_header_df.columns else 0
        jrnl_other   = jrnl_total - jrnl_posted
        jrnl_amt     = jrnl_header_df["Amount"].sum() if "Amount" in jrnl_header_df.columns else 0
        jrnl_amt_p   = (jrnl_header_df[jrnl_header_df["Posted"] == JRNL_PUSH_STATUS]["Amount"].sum()
                        if "Amount" in jrnl_header_df.columns and "Posted" in jrnl_header_df.columns else 0)
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi kpi-total"><div class="kpi-label">Total Journal Entries</div><div class="kpi-count">{jrnl_total}</div><div class="kpi-amount">{fmt_inr(jrnl_amt)} total</div></div>
            <div class="kpi kpi-invoice"><div class="kpi-label">✅ Posted — Ready to Push</div><div class="kpi-count">{jrnl_posted}</div><div class="kpi-amount">{fmt_inr(jrnl_amt_p)}</div></div>
            <div class="kpi kpi-closed"><div class="kpi-label">⏳ Not Posted</div><div class="kpi-count">{jrnl_other}</div><div class="kpi-amount">Excluded from push</div></div>
            <div class="kpi kpi-total"><div class="kpi-label">📋 Line Items</div><div class="kpi-count">{len(jrnl_lines_df)}</div><div class="kpi-amount">{"Subform loaded" if jrnl_has_lines else "Header only"}</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 18px;
                    font-size:13px;color:#8b949e;margin-bottom:18px;display:flex;gap:24px;flex-wrap:wrap;">
            <span>🟡 <b style="color:#e3b341">Posted (Y)</b> → Tally <b>Journal Voucher</b></span>
            <span>⚙ Header: FNCTRANS &nbsp;|&nbsp; Lines: FNCITEMS</span>
            <span>💰 Pure ledger-to-ledger — no stock movement</span>
        </div>""", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    _jrnl_all_pool = jrnl_raw

    # ── Filters — hoisted ABOVE st.tabs() so all 3 tabs share the same result ──
    st.markdown('<p class="sec">Entry Journals — FNCTRANS</p>', unsafe_allow_html=True)
    jf1, jf2, jf3, jf4 = st.columns([2, 2, 2, 4])
    with jf1:
        _jrnl_today = datetime.today().date()
        jrnl_date_preset = st.selectbox(
            "Date:", ["All Dates", "Today", "Yesterday", "Last 7 Days", "This Month", "Custom Range"],
            key="jrnl_date",
        )
    jrnl_date_from = jrnl_date_to = None
    if jrnl_date_preset == "Today":
        jrnl_date_from = jrnl_date_to = _jrnl_today
    elif jrnl_date_preset == "Yesterday":
        jrnl_date_from = jrnl_date_to = _jrnl_today - timedelta(days=1)
    elif jrnl_date_preset == "Last 7 Days":
        jrnl_date_from = _jrnl_today - timedelta(days=6); jrnl_date_to = _jrnl_today
    elif jrnl_date_preset == "This Month":
        jrnl_date_from = _jrnl_today.replace(day=1); jrnl_date_to = _jrnl_today
    elif jrnl_date_preset == "Custom Range":
        with jf2:
            jrnl_date_from = st.date_input("From:", value=_jrnl_today.replace(day=1), key="jrnl_dfrom")
        with jf3:
            jrnl_date_to   = st.date_input("To:", value=_jrnl_today, key="jrnl_dto")
    with jf4:
        jrnl_search = st.text_input(
            "Search Entry No. / Reference / Details:",
            placeholder="e.g. 27000234", key="jrnl_search",
        )

    # ── Apply filters — always runs before any tab body executes ───────────────
    jrnl_filt = jrnl_merged_df.copy() if not jrnl_merged_df.empty else pd.DataFrame()
    if not jrnl_filt.empty:
        if jrnl_search.strip():
            mask = pd.Series(False, index=jrnl_filt.index)
            for col in ["Entry No.", "Internal No.", "Reference", "Details", "Debit Account Desc", "Credit Account Desc"]:
                if col in jrnl_filt.columns:
                    mask |= jrnl_filt[col].astype(str).str.contains(jrnl_search.strip(), case=False, na=False)
            jrnl_filt = jrnl_filt[mask]
        if (jrnl_date_from or jrnl_date_to) and "Transaction Date" in jrnl_filt.columns:
            _jd = pd.to_datetime(jrnl_filt["Transaction Date"], errors="coerce").dt.date
            if jrnl_date_from:
                jrnl_filt = jrnl_filt[_jd.apply(lambda d: d is not None and not isinstance(d, float) and not (hasattr(d, '__class__') and d.__class__.__name__ == 'NaTType') and d >= jrnl_date_from)]
            if jrnl_date_to:
                jrnl_filt = jrnl_filt[_jd.apply(lambda d: d is not None and not isinstance(d, float) and not (hasattr(d, '__class__') and d.__class__.__name__ == 'NaTType') and d <= jrnl_date_to)]

    # Build filtered raw pool by positional index — safe even when TRANSCPTNTH is None
    # jrnl_merged_df rows are in the same order as jrnl_raw (build_jrnl_merged_df never reorders)
    if not jrnl_filt.empty:
        _jrnl_filtered_indices = jrnl_filt.index.tolist()          # DataFrame row indices
        _jrnl_filtered_raw_pool = [jrnl_raw[i] for i in _jrnl_filtered_indices if i < len(jrnl_raw)]
        _jrnl_filtered_entry_ids = jrnl_filt["Entry No."].astype(str).tolist() if "Entry No." in jrnl_filt.columns else []
    else:
        _jrnl_filtered_indices = []
        _jrnl_filtered_raw_pool = []
        _jrnl_filtered_entry_ids = []

    st.session_state["jrnl_filtered_entries"] = _jrnl_filtered_entry_ids
    _jrnl_filtered_ids_set = set(_jrnl_filtered_entry_ids)

    _jrnl_posted_in_filter = sum(
        1 for r in _jrnl_filtered_raw_pool
        if str(r.get("POSTED", "")).strip() == JRNL_PUSH_STATUS
    )
    jrnl_tab1, jrnl_tab2, jrnl_tab3 = st.tabs([
        f"📒 Journal Entries ({len(jrnl_filt)})",
        "🔍 Line Items Drill-down",
        f"🚀 Sync to Tally ({_jrnl_posted_in_filter} posted)",
    ])

    # ── TAB 1 — Header list ───────────────────────────────────────────────────
    with jrnl_tab1:
        if jrnl_filt.empty:
            st.markdown('<div class="alert alert-warn">⚠ No journal entries returned from Priority ERP (FNCTRANS).</div>', unsafe_allow_html=True)
        else:
            jrnl_disp_cols = [c for c in [
                "Entry No.", "Internal No.", "Transaction Date", "Reference", "Details",
                "Branch / Cost Centre",
                "Debit Account", "Debit Account Desc",
                "Credit Account", "Credit Account Desc", "Amount",
                "Line Count", "Accounts", "Batch Number",
            ] if c in jrnl_filt.columns]

            st.dataframe(
                fmt_cur(jrnl_filt[jrnl_disp_cols], "Amount"),
                use_container_width=True, height=500, hide_index=True,
            )
            st.caption(f"ℹ️ {len(jrnl_filt)} journal entries shown.")
            with st.expander("🔬 Debug — Raw Priority fields for first 3 records"):
                for _dbr in jrnl_raw[:3]:
                    st.json({k: _dbr.get(k) for k in ["FNCNUM","TRANSCPTNTH","TRANSDATE","BALDATE","FNCREF","REFERENCE","DETAILS","POSTED","BRANCHNAME","QPRICE"]})

    # ── TAB 2 — Line items drill-down ─────────────────────────────────────────
    with jrnl_tab2:
        st.markdown('<p class="sec">FNCITEMS — Line Items Drill-down</p>', unsafe_allow_html=True)

        # Build a synthetic lines_df from header Debit/Credit accounts when FNCITEMS is empty
        # Respect the filter applied in Tab 1
        # Filter header rows using same positional indices used for jrnl_filt
        _jrnl_header_for_drill = (
            jrnl_header_df.loc[jrnl_header_df.index.isin(_jrnl_filtered_indices)]
            if _jrnl_filtered_indices and not jrnl_header_df.empty
            else jrnl_header_df
        )
        _jrnl_filtered_ids = _jrnl_filtered_ids_set  # for selectbox filtering below
        if not jrnl_has_lines or jrnl_lines_df.empty:
            st.markdown(
                '<div class="alert alert-info">ℹ FNCITEMS subform returned no rows — '
                'showing header-level Debit / Credit accounts as a 2-leg view.</div>',
                unsafe_allow_html=True,
            )
            # Build synthetic 2-row-per-entry dataframe from header columns
            _synth_rows = []
            for _, hrow in _jrnl_header_for_drill.iterrows():
                _en  = hrow.get("Entry No.", "")
                _dt  = hrow.get("Transaction Date") or hrow.get("Date", "")
                _ref = hrow.get("Reference", "")
                _amt = abs(float(hrow.get("Amount") or 0))
                dr   = str(hrow.get("Debit Account", "") or "").strip()
                dr_d = str(hrow.get("Debit Account Desc", "") or "").strip()
                cr   = str(hrow.get("Credit Account", "") or "").strip()
                cr_d = str(hrow.get("Credit Account Desc", "") or "").strip()
                if dr:
                    _synth_rows.append({"Entry No.": _en, "Date": _dt, "Reference": _ref,
                                        "Account No.": dr, "Account Description": dr_d,
                                        "Debit": _amt, "Credit": 0.0})
                if cr:
                    _synth_rows.append({"Entry No.": _en, "Date": _dt, "Reference": _ref,
                                        "Account No.": cr, "Account Description": cr_d,
                                        "Debit": 0.0, "Credit": _amt})
            _drill_source = pd.DataFrame(_synth_rows) if _synth_rows else pd.DataFrame()
        else:
            # Filter lines_df to only the entries that passed the above header filter.
            # Use the filtered-entry-IDs set; if it is non-empty, restrict; if it IS
            # empty but filtering WAS applied (_jrnl_filtered_indices is set/empty list),
            # also restrict (returns empty).  Only skip filtering when no filter was used.
            if _jrnl_filtered_ids_set:
                _drill_source = (
                    jrnl_lines_df[jrnl_lines_df["Entry No."].astype(str).isin(_jrnl_filtered_ids_set)]
                    if "Entry No." in jrnl_lines_df.columns else jrnl_lines_df
                )
            elif _jrnl_filtered_indices is not None and len(_jrnl_filtered_indices) == 0 and (jrnl_date_from or jrnl_date_to or jrnl_search.strip()):
                # A filter was applied and matched nothing — show empty
                _drill_source = pd.DataFrame(columns=jrnl_lines_df.columns)
            else:
                _drill_source = jrnl_lines_df

        if _drill_source.empty:
            st.markdown('<div class="alert alert-warn">⚠ No account data available to display.</div>', unsafe_allow_html=True)
        else:
            # Use explicit length check — an empty set is falsy in Python, which would
            # incorrectly fall through to showing ALL entries when filters yield 0 results.
            _jrnl_entry_opts = (
                [str(e) for e in _jrnl_filtered_ids if e in _drill_source["Entry No."].astype(str).values]
                if len(_jrnl_filtered_ids) > 0
                else _drill_source["Entry No."].dropna().astype(str).unique().tolist()
            )
            if not _jrnl_entry_opts:
                st.markdown('<div class="alert alert-warn">⚠ No entries in current filter.</div>', unsafe_allow_html=True)
            else:
                picked_entry = st.selectbox("Select Entry No.:", _jrnl_entry_opts, key="jrnl_drill")
                drill = _drill_source[_drill_source["Entry No."].astype(str) == str(picked_entry)]

                if drill.empty:
                    st.caption("No line items found for this entry.")
                else:
                    ref  = drill["Reference"].iloc[0] if "Reference" in drill.columns else ""
                    date = drill["Date"].iloc[0]      if "Date"      in drill.columns else ""
                    st.markdown(f"""
                    <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
                                padding:10px 16px;font-size:13px;color:#c9d1d9;margin-bottom:12px;">
                        <b>Entry:</b> {picked_entry} &nbsp;|&nbsp;
                        <b>Date:</b> {date} &nbsp;|&nbsp;
                        <b>Reference:</b> {ref}
                    </div>""", unsafe_allow_html=True)

                    lcols = [c for c in [
                        "Account No.", "Account Description",
                        "Debit", "Credit", "Balance",
                        "Line Details", "Due Date",
                    ] if c in drill.columns]
                    st.dataframe(
                        fmt_cur(drill[lcols], "Debit", "Credit", "Balance"),
                        use_container_width=True, height=300, hide_index=True,
                    )

                    dr_total = drill["Debit"].sum()  if "Debit"  in drill.columns else 0
                    cr_total = drill["Credit"].sum() if "Credit" in drill.columns else 0
                    st.markdown(f"""
                    <div style="display:flex;gap:24px;font-size:13px;color:#8b949e;margin-top:8px;">
                        <span>📤 <b>Total Debit:</b> {fmt_inr(dr_total)}</span>
                        <span>📥 <b>Total Credit:</b> {fmt_inr(cr_total)}</span>
                        <span>{"✅ Balanced" if abs(dr_total - cr_total) < 0.01 else "⚠️ Imbalanced"}</span>
                    </div>""", unsafe_allow_html=True)

    # ── TAB 3 — Tally Sync ────────────────────────────────────────────────────
    with jrnl_tab3:
        st.markdown('<p class="sec">Tally Sync — Push Posted Journal Entries</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="alert alert-info">'
            'Only <b>Posted (Y)</b> entries are pushed as <b>Journal Voucher</b> (ISINVOICE=No).<br>'
            'Entries without FNCITEMS lines use the header-level Debit/Credit accounts as a 2-leg fallback.<br>'
            '<b>Reference &amp; Date (FNCREF / BALDATE):</b> '
            'If Priority has a Reference No (FNCREF), it is pushed to Tally &lt;REFERENCE&gt; — otherwise omitted. '
            'If Priority has a Date (BALDATE), it is pushed to Tally &lt;DATE&gt; and &lt;REFERENCEDATE&gt; — '
            'this happens even when Reference No is absent.'
            '</div>', unsafe_allow_html=True,
        )

        if not _jrnl_all_pool:
            st.markdown('<div class="alert alert-success">✅ No journal entries found — nothing to push.</div>', unsafe_allow_html=True)
        else:
            # Respect filters applied above tabs — use index-based pool (safe when TRANSCPTNTH is None).
            # IMPORTANT: use explicit None sentinel, NOT truthiness — an empty list [] is falsy but
            # means "filter applied, zero matches", which is different from "no filter was run".
            _jrnl_filtered_pool = _jrnl_filtered_raw_pool if _jrnl_filtered_raw_pool is not None else _jrnl_all_pool
            # Filter controls
            _show_posted_only = st.checkbox("Show Posted (Y) entries only", value=False, key="jrnl_posted_only_filter")
            _display_pool = [r for r in _jrnl_filtered_pool if str(r.get("POSTED", "")).strip() == JRNL_PUSH_STATUS] if _show_posted_only else _jrnl_filtered_pool
            _posted_in_view = sum(1 for r in _display_pool if str(r.get("POSTED", "")).strip() == JRNL_PUSH_STATUS)
            st.caption(f"Showing **{len(_display_pool)}** entr{'y' if len(_display_pool)==1 else 'ies'} | {_posted_in_view} Posted (Y) ready to push.")

            _jrnl_pushed_nos = query_daybook_by_type(JRNL_TALLY_VCH_TYPE) | st.session_state.get("jrnl_tally_nos_override", set())
            selected_jrnl = []
            for _jrnl_idx, rec in enumerate(_display_pool):
                details   = str(rec.get("DETAILS")   or "").strip()
                reference = str(rec.get("FNCREF") or rec.get("REFERENCE") or "").strip()
                fncnum    = str(rec.get("FNCNUM")    or "").strip()
                identifier = fncnum or f"#{_jrnl_idx + 1}"
                amount    = abs(float(rec.get("QPRICE") or 0))
                is_posted = str(rec.get("POSTED", "")).strip() == JRNL_PUSH_STATUS
                n_lines   = len(rec.get(JRNL_SUBFORM, []))
                already_pushed = fncnum and fncnum in _jrnl_pushed_nos
                posted_badge = " 🟢 **[POSTED]**" if is_posted else " 🔴 [Not Posted]"
                dup_badge = " ⚠️ **[Already Pushed]**" if already_pushed else ""
                lbl_extra = f" — {n_lines} line(s)" if n_lines else " — 2-leg (header)"
                lbl = f"**{identifier}** — {details or reference or '—'} — {fmt_inr(amount)}{lbl_extra}{posted_badge}{dup_badge}"
                if st.checkbox(
                    lbl,
                    value=False,
                    disabled=already_pushed,
                    key=f"jrnl_chk_{identifier}_{_jrnl_idx}",
                ) and not already_pushed:
                    selected_jrnl.append(rec)

            st.markdown("---")
            jrnl_dry = st.checkbox("Dry run (preview XML only — do not push)", value=False, key="jrnl_dry")
            if st.button(
                f"{'🧪 Dry Run' if jrnl_dry else '🚀 Push'} {len(selected_jrnl)} Journal Entr{'y' if len(selected_jrnl)==1 else 'ies'} to Tally",
                key="jrnl_push_btn",
            ):
                if not selected_jrnl:
                    st.warning("No entries selected.")
                else:
                    jrnl_results = run_jrnl_push(selected_jrnl, jrnl_dry, "JRNL-Posted")
                    st.markdown('<p class="sec">Push Results</p>', unsafe_allow_html=True)
                    df_res = pd.DataFrame(jrnl_results)
                    res_cols = ["Entry No.", "Reference", "Amount", "Tally Type", "Result", "Timestamp"]
                    st.dataframe(df_res[[c for c in res_cols if c in df_res.columns]], use_container_width=True, hide_index=True)
                    ok_n  = sum(1 for r in jrnl_results if "✅" in str(r.get("Result", "")))
                    err_n = sum(1 for r in jrnl_results if "❌" in str(r.get("Result", "")))
                    skp_n = sum(1 for r in jrnl_results if "⚠️" in str(r.get("Result", "")))
                    if jrnl_dry:
                        st.markdown('<div class="alert alert-warn">🧪 Dry run complete — uncheck to push for real.</div>', unsafe_allow_html=True)
                    elif ok_n:
                        st.markdown(f'<div class="alert alert-success">✅ {ok_n} Journal Voucher(s) created in Tally. {err_n} error(s), {skp_n} skipped.</div>', unsafe_allow_html=True)
                    if err_n and not jrnl_dry:
                        st.markdown(
                            f'<div class="alert alert-error">❌ {err_n} failed — verify:<br>'
                            f'• Tally Gateway active on port 9000<br>'
                            f'• "Journal" voucher type exists in Tally<br>'
                            f'• All ledger names in Priority exactly match Tally ledger names</div>',
                            unsafe_allow_html=True,
                        )
                        with st.expander("🔬 View XML for failed entries (check ledger names)"):
                            for _fr in jrnl_results:
                                if "❌" in str(_fr.get("Result", "")) and _fr.get("XML"):
                                    st.markdown(f"**{_fr.get('Entry No.', '?')}** — {_fr.get('Reference', '')}")
                                    st.code(_fr["XML"], language="xml")
                    # Track successfully pushed journal nos to prevent re-push
                    if not jrnl_dry:
                        _pushed_nos = {str(r.get("Entry No.", "")).strip() for r in jrnl_results if "✅" in str(r.get("Result", ""))}
                        _existing = st.session_state.get("jrnl_tally_nos_override", set())
                        st.session_state["jrnl_tally_nos_override"] = _existing | _pushed_nos
                    if "push_log" not in st.session_state:
                        st.session_state.push_log = []
                    st.session_state.push_log.extend(jrnl_results)

            # XML preview expander
            with st.expander("🔬 Preview XML for selected entries"):
                for rec in selected_jrnl[:3]:
                    entry_no = str(rec.get("FNCNUM") or rec.get("TRANSCPTNTH") or rec.get("Entry No.", "?")).strip()
                    xml_preview = build_jrnl_xml(rec)
                    st.markdown(f"**{entry_no}** — {rec.get('DETAILS', rec.get('REFERENCE', ''))}")
                    if xml_preview:
                        st.code(xml_preview, language="xml")
                    else:
                        st.caption("⚠️ No ledger legs found — this entry will be skipped.")
