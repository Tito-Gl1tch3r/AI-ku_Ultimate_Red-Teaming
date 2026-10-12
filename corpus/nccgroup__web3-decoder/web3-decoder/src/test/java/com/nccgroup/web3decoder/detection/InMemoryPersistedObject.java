package com.nccgroup.web3decoder.detection;

import burp.api.montoya.core.ByteArray;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.persistence.PersistedList;
import burp.api.montoya.persistence.PersistedObject;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Minimal in-memory PersistedObject test double. Implements only the methods
 * used by DetectedAbiStore (String / Long / child-object operations). All
 * other interface methods throw UnsupportedOperationException, except the
 * "*Keys()" accessors which return an empty Set for safety.
 */
final class InMemoryPersistedObject implements PersistedObject {

    private final Map<String, String> strings = new HashMap<>();
    private final Map<String, Long> longs = new HashMap<>();
    private final Map<String, PersistedObject> children = new HashMap<>();

    // ---- String ----
    @Override public String getString(String key) { return strings.get(key); }
    @Override public void setString(String key, String value) { strings.put(key, value); }
    @Override public void deleteString(String key) { strings.remove(key); }
    @Override public Set<String> stringKeys() { return new HashSet<>(strings.keySet()); }

    // ---- Long ----
    @Override public Long getLong(String key) { return longs.get(key); }
    @Override public void setLong(String key, long value) { longs.put(key, value); }
    @Override public void deleteLong(String key) { longs.remove(key); }
    @Override public Set<String> longKeys() { return new HashSet<>(longs.keySet()); }

    // ---- Child PersistedObject ----
    @Override public PersistedObject getChildObject(String key) { return children.get(key); }
    @Override public void setChildObject(String key, PersistedObject value) { children.put(key, value); }
    @Override public void deleteChildObject(String key) { children.remove(key); }
    @Override public Set<String> childObjectKeys() { return new HashSet<>(children.keySet()); }

    // ---- Unused: Boolean ----
    @Override public Boolean getBoolean(String key) { throw new UnsupportedOperationException(); }
    @Override public void setBoolean(String key, boolean value) { throw new UnsupportedOperationException(); }
    @Override public void deleteBoolean(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> booleanKeys() { return Collections.emptySet(); }

    // ---- Unused: Byte ----
    @Override public Byte getByte(String key) { throw new UnsupportedOperationException(); }
    @Override public void setByte(String key, byte value) { throw new UnsupportedOperationException(); }
    @Override public void deleteByte(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> byteKeys() { return Collections.emptySet(); }

    // ---- Unused: Short ----
    @Override public Short getShort(String key) { throw new UnsupportedOperationException(); }
    @Override public void setShort(String key, short value) { throw new UnsupportedOperationException(); }
    @Override public void deleteShort(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> shortKeys() { return Collections.emptySet(); }

    // ---- Unused: Integer ----
    @Override public Integer getInteger(String key) { throw new UnsupportedOperationException(); }
    @Override public void setInteger(String key, int value) { throw new UnsupportedOperationException(); }
    @Override public void deleteInteger(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> integerKeys() { return Collections.emptySet(); }

    // ---- Unused: ByteArray ----
    @Override public ByteArray getByteArray(String key) { throw new UnsupportedOperationException(); }
    @Override public void setByteArray(String key, ByteArray value) { throw new UnsupportedOperationException(); }
    @Override public void deleteByteArray(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> byteArrayKeys() { return Collections.emptySet(); }

    // ---- Unused: HttpRequest ----
    @Override public HttpRequest getHttpRequest(String key) { throw new UnsupportedOperationException(); }
    @Override public void setHttpRequest(String key, HttpRequest value) { throw new UnsupportedOperationException(); }
    @Override public void deleteHttpRequest(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> httpRequestKeys() { return Collections.emptySet(); }

    @Override public PersistedList<HttpRequest> getHttpRequestList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setHttpRequestList(String key, PersistedList<HttpRequest> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteHttpRequestList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> httpRequestListKeys() { return Collections.emptySet(); }

    // ---- Unused: HttpResponse ----
    @Override public HttpResponse getHttpResponse(String key) { throw new UnsupportedOperationException(); }
    @Override public void setHttpResponse(String key, HttpResponse value) { throw new UnsupportedOperationException(); }
    @Override public void deleteHttpResponse(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> httpResponseKeys() { return Collections.emptySet(); }

    @Override public PersistedList<HttpResponse> getHttpResponseList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setHttpResponseList(String key, PersistedList<HttpResponse> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteHttpResponseList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> httpResponseListKeys() { return Collections.emptySet(); }

    // ---- Unused: HttpRequestResponse ----
    @Override public HttpRequestResponse getHttpRequestResponse(String key) { throw new UnsupportedOperationException(); }
    @Override public void setHttpRequestResponse(String key, HttpRequestResponse value) { throw new UnsupportedOperationException(); }
    @Override public void deleteHttpRequestResponse(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> httpRequestResponseKeys() { return Collections.emptySet(); }

    @Override public PersistedList<HttpRequestResponse> getHttpRequestResponseList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setHttpRequestResponseList(String key, PersistedList<HttpRequestResponse> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteHttpRequestResponseList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> httpRequestResponseListKeys() { return Collections.emptySet(); }

    // ---- Unused: typed lists ----
    @Override public PersistedList<Boolean> getBooleanList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setBooleanList(String key, PersistedList<Boolean> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteBooleanList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> booleanListKeys() { return Collections.emptySet(); }

    @Override public PersistedList<Short> getShortList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setShortList(String key, PersistedList<Short> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteShortList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> shortListKeys() { return Collections.emptySet(); }

    @Override public PersistedList<Integer> getIntegerList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setIntegerList(String key, PersistedList<Integer> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteIntegerList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> integerListKeys() { return Collections.emptySet(); }

    @Override public PersistedList<Long> getLongList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setLongList(String key, PersistedList<Long> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteLongList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> longListKeys() { return Collections.emptySet(); }

    @Override public PersistedList<String> getStringList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setStringList(String key, PersistedList<String> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteStringList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> stringListKeys() { return Collections.emptySet(); }

    @Override public PersistedList<ByteArray> getByteArrayList(String key) { throw new UnsupportedOperationException(); }
    @Override public void setByteArrayList(String key, PersistedList<ByteArray> value) { throw new UnsupportedOperationException(); }
    @Override public void deleteByteArrayList(String key) { throw new UnsupportedOperationException(); }
    @Override public Set<String> byteArrayListKeys() { return Collections.emptySet(); }
}
