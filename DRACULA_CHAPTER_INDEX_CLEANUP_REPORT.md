# Dracula Chapter Index Cleanup Report

Status: READY_FOR_REVIEW_PENDING_VALIDATION

## Issue

Some Dracula chapter titles can arrive from source/import data with display-unfriendly continuation markers, including variants such as:

- `-- continued`
- `- continued`
- `continued`
- markdown emphasis markers
- all-caps chapter labels

These markers are useful as source/debug evidence but weaken the public reader and table-of-contents experience.

## Fix

Added shared display-title normalization in `frontend/src/lib/controlledLaunch.js`:

- Removes trailing continuation markers.
- Removes simple markdown emphasis markers.
- Normalizes repeated whitespace.
- Converts all-caps chapter headings into calmer display casing.
- Preserves chapter numerals.
- Preserves non-English text when title casing would be unsafe.

Applied the helper in:

- `frontend/src/pages/Reader.jsx` reader chapter index
- `frontend/src/pages/Reader.jsx` reader topbar
- `frontend/src/pages/BookDetail.jsx` chapter list

## Example Outcomes

| Raw title | Display title |
| --- | --- |
| `CHAPTER I. JONATHAN HARKER'S JOURNAL -- continued` | `Chapter I. Jonathan Harker's Journal` |
| `CHAPTER II -- continued` | `Chapter II` |
| `Chapter 3 continued` | `Chapter 3` |

## Public Guardrails

- This is display normalization only.
- It does not alter source text, reader content, payments, or audio.
- It does not publish any new title.
- Public audio remains blocked.
