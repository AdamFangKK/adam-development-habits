def word_break(text, words):
    if not text:
        return True
    return any(text.startswith(word) and word_break(text[len(word) + 1:], words) for word in words)
