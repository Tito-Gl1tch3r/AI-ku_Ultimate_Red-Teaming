import codecs
from ast import literal_eval

def normalize_escapes(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)

    candidates = []

    try:
        if ('\\u' in s) or ('\\x' in s) or ('\\U' in s):
            c = codecs.decode(s, 'unicode_escape')
            candidates.append(c)
    except Exception:
        pass

    try:
        c = s.encode('latin-1').decode('utf-8')
        candidates.append(c)
    except Exception:
        pass

    try:
        c = codecs.decode(s, 'unicode_escape')
        c = c.encode('latin-1').decode('utf-8')
        candidates.append(c)
    except Exception:
        pass

    try:
        tmp = s.encode('latin-1').decode('unicode_escape')
        candidates.append(tmp)
    except Exception:
        pass

    candidates.append(s)

    def score(x: str) -> int:
        return sum(1 for ch in x if ord(ch) > 127)

    best = max(candidates, key=score)
    return best
