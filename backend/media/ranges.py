"""Exact current single-Range parsing and response validation helpers."""

from __future__ import annotations

import re
from typing import Optional, Tuple


def parse_byte_range(range_header: str, total_size: int) -> Tuple[Optional[str], int]:
    value = (range_header or "").strip()
    if not value:
        return None, 200
    match = re.match(r"^bytes=(\d*)-(\d*)$", value)
    if not match:
        return None, 416
    start_raw, end_raw = match.groups()
    if not start_raw and not end_raw:
        return None, 416
    if start_raw:
        start = int(start_raw)
        end = int(end_raw) if end_raw else total_size - 1
    else:
        suffix = int(end_raw)
        if suffix <= 0:
            return None, 416
        start = max(0, total_size - suffix)
        end = total_size - 1
    if start < 0 or end < start or start >= total_size:
        return None, 416
    end = min(end, total_size - 1)
    return f"bytes={start}-{end}", 206


def content_range_header(byte_range: str, total_size: int) -> str:
    match = re.match(r"^bytes=(\d+)-(\d+)$", byte_range or "")
    if not match:
        return f"bytes */{total_size}"
    return f"bytes {match.group(1)}-{match.group(2)}/{total_size}"


def range_content_length(byte_range: str, total_size: int) -> int:
    match = re.match(r"^bytes=(\d+)-(\d+)$", byte_range or "")
    if not match:
        return total_size
    return max(0, int(match.group(2)) - int(match.group(1)) + 1)


def single_range_header_is_well_formed(range_header: str) -> bool:
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", (range_header or "").strip())
    if not match:
        return False
    start_raw, end_raw = match.groups()
    if not start_raw and not end_raw:
        return False
    return not (not start_raw and int(end_raw) <= 0)


def range_response_matches_request(range_header: str, content_range: str, content_length: int) -> bool:
    requested = re.fullmatch(r"bytes=(\d*)-(\d*)", (range_header or "").strip())
    received = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", (content_range or "").strip())
    if not requested or not received:
        return False
    start_raw, end_raw = requested.groups()
    start, end, total = (int(value) for value in received.groups())
    if total <= 0 or start < 0 or end < start or end >= total:
        return False
    if content_length != end - start + 1:
        return False
    if start_raw:
        requested_start = int(start_raw)
        if start != requested_start:
            return False
        requested_end = int(end_raw) if end_raw else total - 1
        return end == min(requested_end, total - 1)
    suffix = int(end_raw)
    return start == max(0, total - suffix) and end == total - 1


def content_range_total_size(content_range: str) -> int:
    match = re.search(r"/(\d+)$", content_range or "")
    if not match:
        return 0
    try:
        return int(match.group(1))
    except ValueError:
        return 0
