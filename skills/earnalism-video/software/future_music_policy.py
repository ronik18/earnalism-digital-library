"""Pure composer compatibility check; no rendering, approvals or file writes.

Historical palette identities are retained for old artifacts. A palette label
cannot make the generic composer satisfy the future continuous-body contract.
"""
FUTURE_PROFILE = 'continuous_open_instrumental_v1'


def require_supported_assembly_music(episode, policy):
    defaults = policy.get('music', {})
    selected = episode.get('music', {})
    if not isinstance(defaults, dict) or not isinstance(selected, dict):
        raise ValueError('Music policy/job settings must be objects')
    future = defaults.get('future_profile')
    if future is None:
        return  # Older policy compatibility; establishes no continuous-body qualification.
    if not isinstance(future, dict) or future.get('id') != FUTURE_PROFILE:
        raise ValueError('Unknown future music profile; review a supported full-body composer')
    palette = selected.get('palette', defaults.get('palette', 'legacy'))
    raise ValueError(
        'New assembly requires ' + FUTURE_PROFILE + '; generic studio.score.compose '
        'with palette ' + str(palette) + ' has no supported full-body composer. '
        'Use a compatible full-body instrumental composer with actual main-start-to-end '
        'coverage, unchanged clear narration and exact approved END video/own audio '
        'without music bleed. Relabeling a palette or disabling the main-video bed '
        'does not qualify this composer. Existing candidate '
        'checks and frozen/mux-only routes remain available.')
