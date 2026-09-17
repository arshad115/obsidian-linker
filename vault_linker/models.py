from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class LinkPhrase:
    phrase: str
    canonical: str
    source_file: str

    @property
    def phrase_lower(self) -> str:
        return self.phrase.lower()


@dataclass
class LinkChange:
    file: str
    line: int
    matched_text: str
    wikilink: str


@dataclass
class LinkResult:
    edited_files: Set[str] = field(default_factory=set)
    total_links_added: int = 0
    changes: list = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
