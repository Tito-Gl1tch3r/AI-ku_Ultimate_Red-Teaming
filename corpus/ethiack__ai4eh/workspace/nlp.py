import sys
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from collections import Counter
import re


def extract_keywords(filename, min_length=3, max_length=30):
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)

    tokens = word_tokenize(text)

    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    keywords = []
    for token in tokens:
        if (
            len(token) >= min_length
            and len(token) <= max_length
            and token not in stop_words
            and not token.isdigit()
            and re.match(r"^[a-zA-Z][a-zA-Z0-9]*$", token)
        ):
            lemmatized = lemmatizer.lemmatize(token)
            keywords.append(lemmatized)

    word_freq = Counter(keywords)

    unique_keywords = sorted(word_freq.keys(), key=lambda x: (-word_freq[x], x))

    return unique_keywords


if __name__ == "__main__":
    keywords = extract_keywords(sys.argv[1])
    for keyword in keywords:
        print(keyword)
