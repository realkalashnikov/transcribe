import re
from typing import List, Dict, Any, Optional

# Lazy singletons
_KAKASI = None

def _get_kakasi():
    global _KAKASI
    if _KAKASI is None:
        try:
            import pykakasi
            _KAKASI = pykakasi.kakasi()
        except ImportError:
            _KAKASI = False
    return _KAKASI

# Mapeamento fonético direto para cirílico (Russo / Ucraniano / Búlgaro)
_CYRILLIC_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu',
    'Я': 'Ya'
}

class TransliterationService:
    @staticmethod
    def is_supported(lang_code: Optional[str]) -> bool:
        if not lang_code:
            return False
        clean = lang_code.lower().strip()
        return clean in {"ja", "jp", "japanese", "zh", "cn", "chinese", "ru", "ru-ru", "russian", "uk", "ukrainian"}

    @staticmethod
    def romanize(text: str, language: Optional[str] = None) -> str:
        if not text or not text.strip():
            return ""

        lang = (language or "").lower().strip()

        # Japonês (Romaji Hepburn)
        if lang in {"ja", "jp", "japanese"}:
            k = _get_kakasi()
            if k:
                conv = k.convert(text)
                romaji_parts = [item['hepburn'] for item in conv if item.get('hepburn')]
                return " ".join(romaji_parts).strip()

        # Chinês (Pinyin com acentos)
        if lang in {"zh", "cn", "chinese"}:
            try:
                import pypinyin
                py_list = pypinyin.pinyin(text, style=pypinyin.Style.TONE)
                words = [p[0] for p in py_list if p]
                return " ".join(words).strip()
            except ImportError:
                pass

        # Cirílico (Russo / Ucraniano)
        if lang in {"ru", "ru-ru", "russian", "uk", "ukrainian"}:
            res = []
            for ch in text:
                res.append(_CYRILLIC_MAP.get(ch, ch))
            return "".join(res).strip()

        return text

    @classmethod
    def romanize_segments(cls, segments: List[Dict[str, Any]], language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Adiciona o campo 'romanized' a cada segmento."""
        updated = []
        for s in segments:
            item = dict(s)
            item["romanized"] = cls.romanize(s.get("text", ""), language=language)
            updated.append(item)
        return updated
