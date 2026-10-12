package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.CacheInterface;
import com.codehack.JungleConfig.Core.JJacksonModule;
import com.codehack.JungleConfig.Core.TypeConverter;
import com.codehack.JungleConfig.Core.TypeConverterAdapter;
import com.codehack.JungleConfig.DataModel.TypeMap;
import com.codehack.JungleConfig.Exceptions.InvalidConfigFormatException;
import com.codehack.JungleConfig.Utils.JLogger;
import com.fasterxml.jackson.core.type.TypeReference;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public class NativeTypeConverter implements TypeConverter {
    private CacheInterface manager;
    private Map<String, TypeConverterAdapter> Adapters = new HashMap<>();
    private boolean FALLBACK_TO_SERIALIZE = false;

    public NativeTypeConverter(CacheInterface manager, boolean FALLBACK_TO_SERIALIZE,TypeConverterAdapter... Adapters) {
        this.manager = manager;
        this.FALLBACK_TO_SERIALIZE = FALLBACK_TO_SERIALIZE;
        for (TypeConverterAdapter ad : Adapters) {
            this.Adapters.put(ad.getType(),ad);
        }

    }
    private Map.Entry<String,String> ConvertToSave(Object dataObj,String type){
        if (type.equals("Json")) return Map.entry("Json",JJacksonModule.ConvertToJson(dataObj));
        if (type.isBlank()) type = dataObj.getClass().getSimpleName();
        if (Adapters.containsKey(type)){
            return Map.entry(type,Adapters.get(type).ConvertToSave(dataObj));
        }
        JLogger.LogWarn(Adapters.keySet().toString());
        JLogger.LogWarn("Default Converters Failed, Using jackson for Type: "+type);
        if (FALLBACK_TO_SERIALIZE){
            String json = JJacksonModule.ConvertToJson(dataObj);
            return Map.entry("Json",json);
        }
        throw new InvalidConfigFormatException();
    }
    @SuppressWarnings("unchecked")
    private <T>T ConvertToUse(String dataObj, String type, Class<T> converTo){
        if (type.equals("Json")||!Adapters.containsKey(converTo.getSimpleName())){
            return JJacksonModule.ConvertToObject(dataObj,converTo);
        }
        return (T) Adapters.get(converTo.getSimpleName()).CastToUse(dataObj);
    }

    @Override
    public void Set(String key, Object data) {
        Map.Entry<String,String> d = ConvertToSave(data,"");
        manager.Set(new TypeMap.Entry<>(key,d.getKey(),d.getValue()));
    }
    @Override
    public void Set(String key, Object data,String type) {
        Map.Entry<String,String> d = ConvertToSave(data,type);
        manager.Set(new TypeMap.Entry<>(key,d.getKey(),d.getValue()));
    }
    @Override
    public void SetPOJO(String key, Object pojo) {
        Map.Entry<String,String> d = ConvertToSave(pojo,"Json");
        manager.Set(new TypeMap.Entry<>(key,d.getKey(),d.getValue()));
    }

    @Override
    public <T> T get(String key, Class<T> type) {
        TypeMap.Entry<String,String,String> dta = manager.Get(key);
        if (dta==null) return null;
        return ConvertToUse(dta.getValue2(),dta.getValue1(),type);
    }

    @Override
    public <T> Optional<T> Get(String key, Class<T> type) {
        TypeMap.Entry<String,String,String> dta = manager.Get(key);
        if (dta==null) return Optional.empty();
        return Optional.of(ConvertToUse(dta.getValue2(),dta.getValue1(),type));
    }

    @Override
    public <T> T getCollection(String key, TypeReference<T> type) {
        TypeMap.Entry<String,String,String> dta = manager.Get(key);
        if (dta==null) return null;
        return JJacksonModule.ConvertToObject(dta.getValue2(),type);
    }

    @Override
    public <T> Optional<T> GetCollection(String key, TypeReference<T> type) {
        TypeMap.Entry<String,String,String> dta = manager.Get(key);
        if (dta==null) return Optional.empty();
        return Optional.of(JJacksonModule.ConvertToObject(dta.getValue2(),type));
    }

    @Override
    public boolean Remove(String key) {
        return manager.Remove(key);
    }

    @Override
    public void BeginTransaction() {
        manager.BeginTransaction();
    }

    @Override
    public void EndTransaction() {
        manager.EndTransaction();
    }

    @Override
    public void Commit() {
        manager.Commit();
    }

    @Override
    public void Rollback() {
        manager.rollback();
    }

    @Override
    public void InvalidateCache() {
        manager.InvalidateCache();
    }

    @Override
    public boolean Backup(File path, boolean override){
        return manager.Backup(path,override);
    }

    @Override
    public TypeMap<String,String,String> query(boolean iKey, String keyReg, boolean iType, String typeReg, boolean iVal, String valReg){
        return manager.query(iKey,keyReg,iType,typeReg,iVal,valReg);
    }

    @Override
    public void removeAll() {
        manager.RemoveAll();
    }
    @Override
    public boolean Exists(String key){
        return manager.Exists(key);
    }
    @Override
    public List<String> getAllKeys(){
        return manager.getAllKeys();
    }
    @Override
    public String getTypeSimpleName(String key){
        return manager.getTypeSimpleName(key);
    }
    @Override
    public List<String> getAllKeys(String regx){
        return manager.getAllKeys(regx);
    }
}
