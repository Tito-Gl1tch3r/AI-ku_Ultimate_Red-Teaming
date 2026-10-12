package com.nccgroup.web3decoder.ui.editor;

import java.util.Objects;

/** A half-open [start, end) range of document text and the style it should get. */
public final class StyleSpan {
    public final int start;
    public final int end; // exclusive
    public final StyleKind kind;
    /** Render this span bold (on top of its kind's colour) — e.g. function-argument keys/values. */
    public final boolean bold;

    public StyleSpan(int start, int end, StyleKind kind) {
        this(start, end, kind, false);
    }

    public StyleSpan(int start, int end, StyleKind kind, boolean bold) {
        this.start = start;
        this.end = end;
        this.kind = kind;
        this.bold = bold;
    }

    public int length() {
        return end - start;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof StyleSpan)) return false;
        StyleSpan s = (StyleSpan) o;
        return start == s.start && end == s.end && kind == s.kind && bold == s.bold;
    }

    @Override
    public int hashCode() {
        return Objects.hash(start, end, kind, bold);
    }

    @Override
    public String toString() {
        return kind + (bold ? "*" : "") + "[" + start + "," + end + ")";
    }
}
