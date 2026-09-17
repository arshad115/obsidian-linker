from typing import Iterable, Set


def load_ignore_phrases(
    phrases: Iterable[str] = (),
    ignore_file: str = None,
) -> Set[str]:
    ignored = {phrase.strip().lower() for phrase in phrases if phrase.strip()}

    if ignore_file:
        with open(ignore_file, 'r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignored.add(line.lower())

    return ignored
