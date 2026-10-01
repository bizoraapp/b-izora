#!/usr/bin/env python3
"""PostToolUse hook for Edit / Write / MultiEdit.
After a change to index.html: syntax, protected functions, EN/FR parity, trap warnings.
After a change to service-worker.js: syntax plus the PREVIOUS_CACHE_VERSION reminder.
Failures are returned to Claude as a blocking message; warnings as extra context."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bizora_checks as bc  # noqa: E402


def emit(fails, warns, summary):
    if fails:
        print(json.dumps({
            'decision': 'block',
            'reason': 'Bizora post-edit checks FAILED (' + summary + '):\n- ' + '\n- '.join(fails) +
                      '\nFix this before doing anything else. Do not weaken a check to make it pass.',
        }))
    elif warns:
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': 'Bizora checks passed (' + summary + ') with warnings:\n- ' + '\n- '.join(warns) +
                                 '\nIf a warning is intended and approved, say so in the report.'}}))
    return 0


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get('tool_input') or {}
    path = os.path.basename(ti.get('file_path') or '')
    if path == 'index.html':
        f, w, s = bc.check_app()
        return emit(f, w, s)
    if path == 'service-worker.js':
        f, w = bc.check_sw()
        return emit(f, w, 'service-worker.js')
    return 0


if __name__ == '__main__':
    sys.exit(main())
