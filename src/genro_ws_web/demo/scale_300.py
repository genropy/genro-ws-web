# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Scale demo, 300 rows. The shape lives in scale_base."""

from __future__ import annotations

from .scale_base import ScaleGridPage

PAGE_TITLE = "Scale — 300 rows"


class Page(ScaleGridPage):
    rows_count = 300
