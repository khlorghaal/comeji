"""Composite status effects onto a character's 12×12 grid."""


def compose(frame, effects, now):
    cells = list(frame)

    def put(y, x, text):
        for offset, char in enumerate(text):
            if 0 <= y < 12 and 0 <= x + offset < 12:
                cells[y * 12 + x + offset] = char

    phase = int(now / 0.3) % 4
    context = effects.get('context')
    if context is not None:
        # Fill is consumed context; the character remains independently animated.
        used = round((100 - context) * 6 / 100)
        put(0, 2, '[' + '#' * used + ' ' * (6 - used) + ']')
        if context <= 20 and phase % 2 == 0:
            put(2, 10, '!')

    goal = effects.get('goal')
    if goal == 'active':
        put(2, (1, 10, 10, 1)[phase], '*')
    elif goal in {'complete', 'completed'} and now - effects.get('goal_at', 0) < 4:
        put(2, (1, 4, 7, 10)[phase], '*')
        put(2, (10, 7, 4, 1)[phase], '+')
    elif goal == 'blocked':
        put(2, 10, '!')
    elif goal == 'paused':
        put(2, 9, '||')
    elif goal in {'budget_limit', 'usage_limit'}:
        put(2, 9, '!!')

    if now - effects.get('error_at', float('-inf')) < 3:
        put(2, (1, 10, 1, 10)[phase], '!')
    return ''.join(cells)
