package com.nccgroup.web3decoder.detection;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * End-to-end detection: body string -> list of validated, deduplicated ABIs.
 * Stateless. Callers (scan check, integration tests) wrap this with storage and
 * issue-raising logic.
 */
public final class AbiDetectionPipeline {

    private AbiDetectionPipeline() {}

    public static List<DetectedAbi> detect(String body) {
        if (body == null || body.length() < 16) return List.of();
        List<Integer> offsets = AbiTokenScanner.findCandidateOffsets(body);
        boolean[] inStringMap = AbiBoundaryExtractor.computeInStringMap(body);
        Map<String, DetectedAbi> byFingerprint = new LinkedHashMap<>();
        for (int offset : offsets) {
            Optional<String> slice = AbiBoundaryExtractor.extract(body, offset, inStringMap);
            if (slice.isEmpty()) continue;
            Optional<String> canonical = AbiNormalizer.toCanonicalJson(slice.get());
            if (canonical.isEmpty()) continue;
            Optional<DetectedAbi> validated = AbiValidator.validate(canonical.get());
            if (validated.isEmpty()) continue;
            byFingerprint.putIfAbsent(validated.get().fingerprint(), validated.get());
        }
        return new ArrayList<>(byFingerprint.values());
    }
}
