package com.codehack.JungleConfig;

import com.codehack.JungleConfig.Core.Adapters.*;
import com.codehack.JungleConfig.Core.Implim.Cache.*;
import com.codehack.JungleConfig.Core.Implim.Converter.*;
import com.codehack.JungleConfig.Core.Implim.IO.*;
import com.codehack.JungleConfig.Core.Implim.Service.*;
import com.codehack.JungleConfig.Core.Implim.TypeConverter.*;
import com.codehack.JungleConfig.Core.TypeConverterAdapter;
import com.codehack.JungleConfig.Core.InternalServiceInterface;
import com.codehack.JungleConfig.Core.TypeConverter;
import com.codehack.JungleConfig.DataModel.TypeMap;
import com.fasterxml.jackson.core.type.TypeReference;

import java.io.File;
import java.util.List;
import java.util.Optional;

public class JungleConfig {

    private TypeConverter converter;

    public JungleConfig(File file) {
        converter = new NativeTypeConverter(
                new NativeExtendedCache(
                        new NativeInternalTransaction(
                                new NativeInternalCache(
                                        new NativeConverter(
                                                new NativeIOHandler(file)),
                                        10, 100, true))),
                true, getDefaultAdapters());
    }

    public JungleConfig(TypeConverter converter) {
        this.converter = converter;
    }

    public static JungleConfig EncryptedConfig(File file, String password) {
        return new JungleConfig(new NativeTypeConverter(
                new NativeExtendedCache(
                        new NativeInternalTransaction(
                                new NativeInternalCache(
                                        new NativeEncryptedConverter(
                                                new NativeIOHandler(file),
                                                password),
                                        10, 100, true))),
                true, getDefaultAdapters()));
    }

    public static JungleConfig InMemoryConfig() {
        return new JungleConfig(new NativeTypeConverter(
                new NativeExtendedCache(
                        new NativeInternalTransaction(
                                new NativeInternalCache(
                                        new NativeConverter(
                                                new NativeInMemoryIOHandler()),
                                        10, 100, true))),
                true, getDefaultAdapters()));
    }

    public static JungleConfig FlatJsonConfig() {
        return new JungleConfig(new NativeTypeConverter(
                new NativeExtendedCache(
                        new NativeInternalTransaction(
                                new NativeInternalCache(
                                        new NativeFlatJsonConverter(
                                                new NativeInMemoryIOHandler()),
                                        10, 100, true))),
                true, getDefaultAdapters()));
    }

    private static TypeConverterAdapter[] getDefaultAdapters() {
        return new TypeConverterAdapter[] {
                new NativeBooleanAdapter(),
                new NativeIntagerAdapter(),
                new NativeStringAdapter(),
                new NativeLongAdapter(),
                new NativeDoubleAdapter(),
                new NativeFloatAdapter(),
                new NativeUUIDAdapter(),
                new NativeLocalDateAdapter(),
                new NativeLocalDateTimeAdapter(),
                new NativeLocalTimeAdapter()
        };
    }

    public JungleConfig Set(String key, Object data) {
        converter.Set(key, data);
        return this;
    }

    public JungleConfig Set(String key, Object data, String type) {
        converter.Set(key, data, type);
        return this;
    }

    public JungleConfig SetPOJO(String key, Object data) {
        converter.SetPOJO(key, data);
        return this;
    }

    public <T> T get(String key, Class<T> type) {
        return converter.get(key, type);
    }

    public <T> Optional<T> Get(String key, Class<T> type) {
        return converter.Get(key, type);
    }

    public <T> T getCollection(String key, TypeReference<T> type) {
        return converter.getCollection(key, type);
    }

    public <T> Optional<T> GetCollection(String key, TypeReference<T> type) {
        return converter.GetCollection(key, type);
    }

    public boolean Remove(String key) {
        return converter.Remove(key);
    }

    public JungleConfig BeginTransaction() {
        converter.BeginTransaction();
        return this;
    }

    public void EndTransaction() {
        converter.EndTransaction();
    }

    public JungleConfig Commit() {
        converter.Commit();
        return this;
    }

    public JungleConfig Rollback() {
        converter.Rollback();
        return this;
    }

    public void InvalidateCache() {
        converter.InvalidateCache();
    }

    public boolean Backup(File path, boolean override) {
        return converter.Backup(path, override);
    }

    public TypeMap<String, String, String> query(boolean iKey, String keyReg, boolean iType, String typeReg,
            boolean iVal, String valReg) {
        return converter.query(iKey, keyReg, iType, typeReg, iVal, valReg);
    }

    public void RemoveAllKeys() {
        converter.removeAll();
    }

    public boolean Exists(String key) {
        return converter.Exists(key);
    }

    public List<String> getAllKeys() {
        return converter.getAllKeys();
    }

    public List<String> getAllKeys(String regx) {
        return converter.getAllKeys(regx);
    }

    public String getTypeSimpleName(String key) {
        return converter.getTypeSimpleName(key);
    }

    public Optional<String> GetTypeSimpleName(String key) {
        return Optional.of(converter.getTypeSimpleName(key));
    }
}
