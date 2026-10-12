package com.nccgroup.web3decoder.detection;

import java.util.List;
import java.util.Objects;

/** Immutable record of a validated, fingerprinted ABI. */
public final class DetectedAbi {
    private final String fingerprint;   // SHA-256 hex of canonical JSON
    private final String canonicalJson; // strict JSON, sorted keys
    private final List<String> selectors; // unique 4-byte selectors, lowercase "0x..."

    public DetectedAbi(String fingerprint, String canonicalJson, List<String> selectors) {
        this.fingerprint = Objects.requireNonNull(fingerprint);
        this.canonicalJson = Objects.requireNonNull(canonicalJson);
        this.selectors = List.copyOf(selectors);
    }

    public String fingerprint() { return fingerprint; }
    public String canonicalJson() { return canonicalJson; }
    public List<String> selectors() { return selectors; }

    @Override
    public boolean equals(Object o) {
        return o instanceof DetectedAbi d && d.fingerprint.equals(this.fingerprint);
    }
    @Override
    public int hashCode() { return fingerprint.hashCode(); }
}
