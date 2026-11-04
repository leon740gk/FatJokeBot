def plural(count, one, few, many):
    """The word form for the count; Russian and Ukrainian share the rule: 1 раз, 2 раза, 5 раз."""
    if 11 <= count % 100 <= 14:
        return many
    if count % 10 == 1:
        return one
    if count % 10 in (2, 3, 4):
        return few
    return many
