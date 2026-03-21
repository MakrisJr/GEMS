"""Small helpers for readable plain-text report outputs."""


def make_section(title: str, lines) -> str:
    """Return one formatted report section."""
    content = [str(line) for line in lines if str(line).strip()]
    if not content:
        return ""
    underline = "-" * len(title)
    return "\n".join([title, underline, *content])


def make_report(title: str, sections) -> str:
    """Return a simple multi-section text report."""
    blocks = [title, "=" * len(title)]
    for section in sections:
        if not section:
            continue
        blocks.extend(["", section])
    return "\n".join(blocks) + "\n"
