package com.codehack.JungleConfig.Core;

import com.codehack.JungleConfig.DataModel.TypeMap;
import com.fasterxml.jackson.core.type.TypeReference;

import java.io.File;
import java.util.List;
import java.util.Optional;

public interface TypeConverter {
    void Set(String key,Object data);
    void Set(String key,Object data,String Type);
    void SetPOJO(String key,Object pojo);
    <T> T get(String key,Class<T> type);
    <T>Optional<T> Get(String key,Class<T> type);
    <T> T getCollection(String key, TypeReference<T> type);
    <T> Optional<T> GetCollection(String key,TypeReference<T> type);
    boolean Remove(String key);
    void BeginTransaction();
    void EndTransaction();
    void Commit();
    void Rollback();
    void InvalidateCache();

    boolean Backup(File path, boolean override);

    TypeMap<String,String,String> query(boolean iKey, String keyReg, boolean iType, String typeReg, boolean iVal, String valReg);

    void removeAll();

    boolean Exists(String key);

    List<String> getAllKeys();

    String getTypeSimpleName(String key);

    List<String> getAllKeys(String regx);
}
