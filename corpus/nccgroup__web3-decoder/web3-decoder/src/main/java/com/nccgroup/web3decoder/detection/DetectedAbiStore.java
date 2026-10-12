package com.nccgroup.web3decoder.detection;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.persistence.PersistedObject;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;

/**
 * Stores ABIs detected from passive scanning of HTTP responses. Keyed by content
 * fingerprint. Maintains an in-memory {@code selector -> fingerprints} index for
 * O(1) lookup during decode. Persists across Burp restarts via PersistedObject.
 * Enforces a configurable size cap with oldest-first (FIFO) eviction.
 *
 * <p>Persistence shape:
 * <pre>
 * extensionData
 * └── detected_ABIs (PersistedObject)
 *     └── &lt;fingerprint&gt; (PersistedObject)
 *         ├── canonicalJson : String
 *         ├── selectorsCsv  : String   (comma-joined "0x...,0x...")
 *         ├── firstSeenUrl  : String
 *         ├── firstSeenAt   : Long     (epoch millis)
 *         └── _insertOrder  : Long     (monotonic insert counter for FIFO)
 * </pre>
 */
public final class DetectedAbiStore {

    private static final String ROOT_KEY = "detected_ABIs";

    private final MontoyaApi api;
    private final int capacity;
    private final Supplier<PersistedObject> persistedObjectFactory;
    private final PersistedObject root;
    // fingerprint -> DetectedAbi (insertion-ordered for FIFO eviction)
    private final LinkedHashMap<String, DetectedAbi> abis = new LinkedHashMap<>();
    // selector (lowercase) -> list of fingerprints
    private final Map<String, List<String>> selectorIndex = new HashMap<>();
    private final AtomicLong insertCounter = new AtomicLong();

    public DetectedAbiStore(MontoyaApi api, int capacity) {
        this(api, capacity, PersistedObject::persistedObject);
    }

    /**
     * Test-friendly constructor that allows injecting an alternative
     * PersistedObject factory. Production code should use the two-arg ctor,
     * which delegates to the real Montoya factory.
     */
    public DetectedAbiStore(MontoyaApi api, int capacity, Supplier<PersistedObject> persistedObjectFactory) {
        this.api = api;
        this.capacity = capacity;
        this.persistedObjectFactory = persistedObjectFactory;
        this.root = initRoot();
        reloadFromPersistence();
    }

    private PersistedObject initRoot() {
        PersistedObject extData = api.persistence().extensionData();
        PersistedObject po = extData.getChildObject(ROOT_KEY);
        if (po == null) {
            po = persistedObjectFactory.get();
            extData.setChildObject(ROOT_KEY, po);
        }
        return po;
    }

    private void reloadFromPersistence() {
        Set<String> keys = root.childObjectKeys();
        // Order by stored _insertOrder so FIFO eviction state is preserved
        // across restarts.
        List<String> ordered = new ArrayList<>(keys);
        ordered.sort((a, b) -> {
            PersistedObject ea = root.getChildObject(a);
            PersistedObject eb = root.getChildObject(b);
            Long la = ea == null ? null : ea.getLong("_insertOrder");
            Long lb = eb == null ? null : eb.getLong("_insertOrder");
            return Long.compare(la == null ? 0L : la, lb == null ? 0L : lb);
        });
        long maxOrder = 0L;
        for (String fp : ordered) {
            PersistedObject entry = root.getChildObject(fp);
            if (entry == null) continue;
            String json = entry.getString("canonicalJson");
            String csv = entry.getString("selectorsCsv");
            Long order = entry.getLong("_insertOrder");
            if (json == null) continue;
            List<String> selectors = (csv == null || csv.isEmpty())
                    ? List.of() : Arrays.asList(csv.split(","));
            DetectedAbi abi = new DetectedAbi(fp, json, selectors);
            abis.put(fp, abi);
            for (String s : selectors) {
                selectorIndex.computeIfAbsent(s.toLowerCase(), k -> new ArrayList<>()).add(fp);
            }
            if (order != null && order > maxOrder) maxOrder = order;
        }
        insertCounter.set(maxOrder);
    }

    /** @return true if this fingerprint was new (and thus stored). */
    public synchronized boolean saveIfNew(DetectedAbi abi, String sourceUrl) {
        if (abis.containsKey(abi.fingerprint())) return false;

        // Evict oldest entries until we have room
        while (abis.size() >= capacity) {
            String oldest = abis.keySet().iterator().next();
            removeInternal(oldest);
        }

        abis.put(abi.fingerprint(), abi);
        for (String selector : abi.selectors()) {
            selectorIndex.computeIfAbsent(selector.toLowerCase(), k -> new ArrayList<>())
                    .add(abi.fingerprint());
        }

        PersistedObject entry = persistedObjectFactory.get();
        entry.setString("canonicalJson", abi.canonicalJson());
        entry.setString("selectorsCsv", String.join(",", abi.selectors()));
        entry.setString("firstSeenUrl", sourceUrl == null ? "" : sourceUrl);
        entry.setLong("firstSeenAt", System.currentTimeMillis());
        entry.setLong("_insertOrder", insertCounter.incrementAndGet());
        root.setChildObject(abi.fingerprint(), entry);

        return true;
    }

    public synchronized List<DetectedAbi> findBySelector(String selector) {
        if (selector == null) return List.of();
        String normalized = selector.toLowerCase();
        List<String> fps = selectorIndex.get(normalized);
        if (fps == null) return List.of();
        List<DetectedAbi> result = new ArrayList<>(fps.size());
        for (String fp : fps) {
            DetectedAbi a = abis.get(fp);
            if (a != null) result.add(a);
        }
        return Collections.unmodifiableList(result);
    }

    public synchronized int size() {
        return abis.size();
    }

    /** A snapshot of one stored entry with its persisted metadata (URL + timestamp). */
    public static final class Entry {
        private final DetectedAbi abi;
        private final String firstSeenUrl;
        private final long firstSeenAt;

        public Entry(DetectedAbi abi, String firstSeenUrl, long firstSeenAt) {
            this.abi = abi;
            this.firstSeenUrl = firstSeenUrl;
            this.firstSeenAt = firstSeenAt;
        }

        public DetectedAbi abi() { return abi; }
        public String firstSeenUrl() { return firstSeenUrl; }
        public long firstSeenAt() { return firstSeenAt; }
    }

    /** Snapshot of every stored ABI with its persisted metadata. FIFO-ordered (oldest
     *  first), matching the in-memory insertion order used for eviction. */
    public synchronized List<Entry> snapshot() {
        List<Entry> result = new ArrayList<>(abis.size());
        for (DetectedAbi abi : abis.values()) {
            PersistedObject entry = root.getChildObject(abi.fingerprint());
            String url = "";
            long at = 0L;
            if (entry != null) {
                String s = entry.getString("firstSeenUrl");
                if (s != null) url = s;
                Long t = entry.getLong("firstSeenAt");
                if (t != null) at = t;
            }
            result.add(new Entry(abi, url, at));
        }
        return Collections.unmodifiableList(result);
    }

    /** Remove the entry identified by {@code fingerprint} from both the in-memory
     *  index and persistence. @return true if an entry was removed. */
    public synchronized boolean remove(String fingerprint) {
        if (fingerprint == null || !abis.containsKey(fingerprint)) return false;
        removeInternal(fingerprint);
        return true;
    }

    private void removeInternal(String fingerprint) {
        DetectedAbi abi = abis.remove(fingerprint);
        if (abi != null) {
            for (String s : abi.selectors()) {
                String normalized = s.toLowerCase();
                List<String> list = selectorIndex.get(normalized);
                if (list != null) {
                    list.remove(fingerprint);
                    if (list.isEmpty()) selectorIndex.remove(normalized);
                }
            }
        }
        root.deleteChildObject(fingerprint);
    }
}
