import re
from typing import List, Dict, Any

class KeywordMatcher:
    """
    Evaluates alert titles and content against configurable keyword lists and matching rules.
    """

    def __init__(self, keywords: List[str] = None, match_mode: str = "any"):
        self.keywords = keywords or []
        self.match_mode = match_mode.lower()

    def update_rules(self, keywords: List[str], match_mode: str = "any"):
        self.keywords = keywords
        self.match_mode = match_mode.lower()

    def match(self, title: str, content: str = "") -> Dict[str, Any]:
        """
        Checks if title or content matches the keyword rules.

        Returns:
            dict containing:
                - is_match (bool)
                - matched_keywords (List[str])
                - snippet (str)
        """
        combined_text = f"{title}\n{content}"
        matched_keywords = []

        if not self.keywords:
            return {"is_match": False, "matched_keywords": [], "snippet": ""}

        if self.match_mode == "regex":
            for pattern in self.keywords:
                try:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        matched_keywords.append(pattern)
                except re.error:
                    continue
        else:
            for kw in self.keywords:
                # Use word boundary regex for precise keyword matching
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, combined_text, re.IGNORECASE):
                    matched_keywords.append(kw)

        if self.match_mode == "all":
            is_match = len(matched_keywords) == len(self.keywords)
        else:  # default to "any"
            is_match = len(matched_keywords) > 0

        snippet = self._generate_snippet(combined_text, matched_keywords) if is_match else ""

        return {
            "is_match": is_match,
            "matched_keywords": matched_keywords,
            "snippet": snippet
        }

    def _generate_snippet(self, text: str, matched_keywords: List[str], max_len: int = 250) -> str:
        """
        Extracts a snippet surrounding the first matched keyword and highlights keywords.
        """
        if not text:
            return ""

        # Clean text whitespace
        clean_text = " ".join(text.split())

        # Highlight all matched keywords in snippet
        highlighted = clean_text
        for kw in matched_keywords:
            pattern = re.compile(r'\b(' + re.escape(kw) + r')\b', re.IGNORECASE)
            highlighted = pattern.sub(r'**[\1]**', highlighted)

        if len(highlighted) <= max_len:
            return highlighted
        return highlighted[:max_len] + "..."
