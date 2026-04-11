"""
Branding configuration for MaxEnt-Kernel outputs.

All visible fields are fully editable by institutes and researchers.
Hope 'n Mind SASU - Research / MaxEnt-Kernel identity is preserved
invisibly in the metadata of every generated file.

Config location: ~/.maxent-kernel/branding.json
Default: pre-filled with Hope 'n Mind SASU - Research publication info.

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y.
DOI: 10.5281/zenodo.19500872
"""

import json
import os

# ─── Defaults ───────────────────────────────────────────────────────────────

_DEFAULTS = {
    # Top line of the figure header (institution / research group)
    "institute_name": "Hope 'n Mind SASU - Research",
    # Second line — editable subtitle (e.g. authors, experiment name)
    "subtitle":       "Non-Markovian vs Lindblad Dynamics",
    # Third line — generic reference field (DOI, arXiv, grant, etc.)
    "reference":      "DOI: 10.5281/zenodo.19500872",
    # Logo image path (empty = use built-in MaxEnt-Kernel logo)
    "logo_path":      "",
    # Logo placement: "left" or "right"
    "logo_position":  "left",
    # Footer — centered, small text below the figure
    "footer_text":    "MaxEnt-Kernel solver by Hope 'n Mind SASU - Research",
}

# Hidden software signature embedded in file metadata (never shown on figure)
_META_SOFTWARE  = "MaxEnt-Kernel — Non-Markovian Quantum Dynamics Solver"
_META_COPYRIGHT = "Hope 'n Mind SASU - Research — DOI: 10.5281/zenodo.19500872"


def _user_config_path():
    """~/.maxent-kernel/branding.json"""
    return os.path.join(os.path.expanduser("~"), ".maxent-kernel", "branding.json")


# ─── BrandingConfig ─────────────────────────────────────────────────────────

class BrandingConfig:
    """
    Fully editable branding applied to all MaxEnt-Kernel visual outputs.

    Usage:
        cfg = BrandingConfig.load()
        cfg.apply_to_figure(fig)
        header = cfg.summary_header()
        meta   = cfg.metadata_dict()          # embed in savefig
    """

    def __init__(self):
        self.institute_name = _DEFAULTS["institute_name"]
        self.subtitle       = _DEFAULTS["subtitle"]
        self.reference      = _DEFAULTS["reference"]
        self.logo_path      = _DEFAULTS["logo_path"]
        self.logo_position  = _DEFAULTS["logo_position"]
        self.footer_text    = _DEFAULTS["footer_text"]

    # ── Persistence ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls):
        """Load user config, falling back silently to defaults."""
        cfg = cls()
        path = _user_config_path()
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cfg.institute_name = str(data.get("institute_name", _DEFAULTS["institute_name"]))
                cfg.subtitle       = str(data.get("subtitle",       _DEFAULTS["subtitle"]))
                cfg.reference      = str(data.get("reference",      _DEFAULTS["reference"]))
                cfg.logo_path      = str(data.get("logo_path",      ""))
                cfg.logo_position  = str(data.get("logo_position",  "left"))
                cfg.footer_text    = str(data.get("footer_text",    _DEFAULTS["footer_text"]))
            except Exception:
                pass  # fall back to defaults on any error
        return cfg

    def save(self):
        """Persist to ~/.maxent-kernel/branding.json."""
        path = _user_config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "institute_name": self.institute_name,
            "subtitle":       self.subtitle,
            "reference":      self.reference,
            "logo_path":      self.logo_path,
            "logo_position":  self.logo_position,
            "footer_text":    self.footer_text,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def reset_to_defaults(self):
        """Restore all fields to package defaults."""
        for k, v in _DEFAULTS.items():
            setattr(self, k, v)

    # ── Text helpers ─────────────────────────────────────────────────────────

    def summary_header(self):
        """Multi-line text block for the top of summary .txt files."""
        sep = "=" * 55
        lines = [sep]
        if self.institute_name:
            lines.append(f"  {self.institute_name}")
        if self.subtitle:
            lines.append(f"  {self.subtitle}")
        if self.reference:
            lines.append(f"  {self.reference}")
        lines.append(sep)
        return "\n".join(lines)

    # ── File metadata ────────────────────────────────────────────────────────

    def metadata_dict(self, extra=None):
        """
        Return a dict of hidden metadata to embed in saved files.

        MaxEnt-Kernel / Hope 'n Mind identity is always present here,
        invisible in the figure but recorded in the file properties.

        Use metadata_for_format(ext) to get the correctly filtered dict
        for a specific file format — each backend accepts different keys.
        """
        meta = {
            "Title":       self.subtitle or "Non-Markovian vs Lindblad Dynamics",
            "Author":      self.institute_name,
            "Subject":     self.reference,
            "Software":    _META_SOFTWARE,
            "Description": _META_COPYRIGHT,
            "Creator":     _META_SOFTWARE,
            "Keywords":    "non-Markovian, quantum dynamics, Lindblad, MaxEnt-Kernel",
        }
        if extra:
            meta.update(extra)
        return meta

    def metadata_for_format(self, ext, extra=None):
        """
        Return metadata filtered to the keys accepted by each matplotlib backend.

        PNG / TIFF  — Agg backend  : Title, Author, Description, Software,
                                     Copyright, Source, Comment, Warning
        PDF         — pdf backend  : Title, Author, Subject, Keywords,
                                     Creator, Producer  (full support)
        SVG         — svg backend  : title, url, date  (lowercase, 3 keys only)
        EPS         — ps backend   : no metadata= kwarg supported → returns None
                                     (metadata is in DSC comments automatically)

        Returns None for formats that do not support metadata injection,
        so callers can skip the kwarg entirely.
        """
        base = self.metadata_dict(extra)
        ext  = ext.lower().lstrip(".")

        if ext == "pdf":
            return {k: base[k] for k in
                    ("Title", "Author", "Subject", "Keywords", "Creator")
                    if k in base}

        if ext == "png" or ext in ("tiff", "tif"):
            return {k: base[k] for k in
                    ("Title", "Author", "Description", "Software")
                    if k in base}

        # SVG and EPS: metadata= not reliably supported across matplotlib versions
        # The forensic watermark is carried by PNG and PDF exports.
        return None

    # ── Matplotlib integration ────────────────────────────────────────────────

    def apply_to_figure(self, fig, _default_logo_path=None, source_label=None):
        """
        Apply branding to a matplotlib Figure:

          Layout (top area):
            Line 1 — institute_name       (bold, prominent)
            Line 2 — subtitle             (normal weight)
            Line 3 — reference            (small, italic)
          Top-left annotation — spectral density / method used (optional)
          Logo — top-left OR top-right inset
          Footer — centered, small, bottom of figure

        Parameters
        ----------
        fig                : matplotlib.figure.Figure
        _default_logo_path : str | None
            Built-in logo path; used only when logo_path is empty.
        source_label       : str | None
            Spectral density / data source used for this run.
            Displayed as a small italic annotation in the top-left corner,
            just below the header block.
            Example: "J(ω): Lorentzian (cavity)"
        """
        # ── Suptitle: institute (bold) / subtitle / reference ──
        title_parts = []
        if self.institute_name:
            title_parts.append(self.institute_name)
        if self.subtitle:
            title_parts.append(self.subtitle)
        if self.reference:
            title_parts.append(self.reference)

        full_title = "\n".join(title_parts) if title_parts else "MaxEnt-Kernel"

        # Use multi-fontsize trick via two fig.text() calls for contrast
        # Top suptitle handles all three lines — fontsize chosen for the block
        fig.suptitle(
            full_title,
            fontsize=10, fontweight='normal',
            # We'll layer a bold institute name on top via fig.text
        )

        # Override: re-draw just the institute name in bold (same y position)
        if self.institute_name and (self.subtitle or self.reference):
            # Clear suptitle and redraw with styled lines
            fig.texts.clear()   # remove suptitle we just set (it's in fig.texts)
            y_top = 0.985

            # Institute name — bold, slightly larger
            fig.text(0.5, y_top, self.institute_name,
                     ha='center', va='top',
                     fontsize=11, fontweight='bold')

            y_current = y_top - 0.038
            if self.subtitle:
                fig.text(0.5, y_current, self.subtitle,
                         ha='center', va='top',
                         fontsize=10, fontweight='normal')
                y_current -= 0.030

            if self.reference:
                fig.text(0.5, y_current, self.reference,
                         ha='center', va='top',
                         fontsize=8, fontweight='normal',
                         color='#555555', style='italic')

        # ── Source label (spectral density / method) — top-left ──
        if source_label:
            fig.text(
                0.01, 0.895,
                f"J(\u03c9): {source_label}",
                ha='left', va='top',
                fontsize=7.5, color='#444444', style='italic'
            )

        # ── Footer ──
        if self.footer_text:
            fig.text(
                0.5, 0.005, self.footer_text,
                ha='center', va='bottom',
                fontsize=7, color='#888888', style='italic'
            )

        # ── Logo ──
        logo = self.logo_path or _default_logo_path or ""
        if logo and os.path.isfile(logo):
            try:
                import matplotlib.pyplot as plt
                img = plt.imread(logo)
                # left: [x0, y0, width, height] in figure coords
                if self.logo_position == "right":
                    ax_logo = fig.add_axes([0.935, 0.915, 0.055, 0.07])
                else:
                    ax_logo = fig.add_axes([0.005, 0.915, 0.055, 0.07])
                ax_logo.imshow(img)
                ax_logo.axis('off')
            except Exception:
                pass  # logo is cosmetic — never crash the simulation
