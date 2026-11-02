"""Closed exact two-title dispatch; Cedar validation remains unchanged."""
try:
    from . import native_audiobook_replacement as cedar
    from . import open_window_audiobook_replacement as opened
except ImportError:
    import native_audiobook_replacement as cedar
    import open_window_audiobook_replacement as opened


def profile_for_slug(slug):
    if not isinstance(slug,str):return None
    return {cedar.SLUG:cedar,opened.SLUG:opened}.get(slug)


def review_profile(book):
    if not isinstance(book,dict):return None
    profile=profile_for_slug(book.get('slug'));marker=book.get(cedar.FIELD)
    if (profile is None or not isinstance(marker,dict)
        or marker.get('schema_version')!=profile.SCHEMA
        or marker.get('status') not in {'STAGED_PRIVATE','PROMOTED_PUBLIC'}
        or marker.get('candidate_descriptor_sha256')!=profile.DESCRIPTOR):return None
    return profile


def actual_package(profile):
    return opened.finalized_package_binding() if profile is opened else cedar.ACTUAL_PACKAGE


def selected_from_verified_scope(book,scope):
    profile=review_profile(book)
    cedar.need(profile is not None,'Exact two-title review profile unavailable')
    return profile.selected_from_verified_scope(book,scope)
