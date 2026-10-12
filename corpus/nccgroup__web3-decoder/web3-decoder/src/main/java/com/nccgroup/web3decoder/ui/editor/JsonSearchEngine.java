package com.nccgroup.web3decoder.ui.editor;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/** Computes match ranges for the search bar. Pure; no Swing. */
public final class JsonSearchEngine {

    public List<Range> find(String text, String query, boolean caseSensitive, boolean regex) {
        List<Range> ranges = new ArrayList<>();
        if (text == null || text.isEmpty() || query == null || query.isEmpty()) {
            return ranges;
        }

        if (regex) {
            try {
                int flags = caseSensitive ? 0 : (Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);
                Matcher m = Pattern.compile(query, flags).matcher(text);
                // Matcher.find() advances past zero-width matches automatically, so this
                // cannot loop forever; we simply skip empty matches.
                while (m.find()) {
                    if (m.end() > m.start()) {
                        ranges.add(new Range(m.start(), m.end()));
                    }
                }
            } catch (PatternSyntaxException e) {
                return new ArrayList<>(); // invalid regex: no matches
            }
            return ranges;
        }

        String hay = caseSensitive ? text : text.toLowerCase();
        String needle = caseSensitive ? query : query.toLowerCase();
        int from = 0;
        int idx;
        while ((idx = hay.indexOf(needle, from)) >= 0) {
            ranges.add(new Range(idx, idx + needle.length()));
            from = idx + needle.length();
        }
        return ranges;
    }
}
