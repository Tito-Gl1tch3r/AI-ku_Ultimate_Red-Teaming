package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.CacheInterface;
import com.codehack.JungleConfig.Core.ConverterInterface;
import com.codehack.JungleConfig.DataModel.TypeMap;
import com.codehack.JungleConfig.Utils.JLogger;

import java.io.File;
import java.util.List;
import java.util.stream.Collectors;

public class NativeCache implements CacheInterface {
    private ConverterInterface converterInterface;

    private TypeMap<String,String,String> cache = new TypeMap<>();
    private TypeMap<String,String,String> saveQuery = new TypeMap<>();
    private int CACHE_WRITE_INTERVAL = 10;
    private int CACHE_READ_INTERVAL = 100;
    private int Interations = 0;
    private int readInterations =0;
    private boolean useCache;
    private boolean isCacheDirty=true;
    private boolean AutoCommit = true;

    public NativeCache(ConverterInterface converterInterface, int CACHE_WRITE_INTERVAL, int CACHE_READ_INTERVAL, boolean autoCommit,boolean useCache) {
        this.converterInterface = converterInterface;
        this.CACHE_WRITE_INTERVAL = CACHE_WRITE_INTERVAL;
        this.CACHE_READ_INTERVAL = CACHE_READ_INTERVAL;
        this.useCache = useCache;
        AutoCommit = autoCommit;
    }

    private void updateCache(){
        if (((Interations>CACHE_WRITE_INTERVAL)||isCacheDirty||(readInterations>CACHE_READ_INTERVAL))&&AutoCommit){
            cache = converterInterface.decode();
            Interations=0;
            readInterations = 0;
            isCacheDirty = false;
        }
    }
    private TypeMap<String,String,String> Read(){
        if (!useCache) return converterInterface.decode();
        if (!AutoCommit) return midgradeSnapShot(saveQuery);
        updateCache();
        readInterations++;
        return cache;
    }
    private void Write(TypeMap.Entry<String,String,String> data){
        saveQuery.put(data);
        flush();
    }
    public void flush(){
        if (AutoCommit){
            cache = midgradeEdits(saveQuery);
            converterInterface.encode(cache);
            Interations++;
            saveQuery.clear();
        }
    }
    private boolean RemoveEntity(String key){
        boolean x = cache.remove(key);
        boolean y = saveQuery.remove(key);
        if (x||y){
            flush();
            return true;
        }
        return false;
    }
    private TypeMap<String,String,String> midgradeEdits(TypeMap<String,String,String> edits){
        TypeMap<String,String,String> data= Read();
        for (TypeMap.Entry<String,String,String> d:edits.getEntryList()){
            data.put(d);
        }
        return data;
    }
    private TypeMap<String,String,String> midgradeSnapShot(TypeMap<String,String,String> edits){
        TypeMap<String,String,String> data= cache;
        for (TypeMap.Entry<String,String,String> d:edits.getEntryList()){
            data.put(d);
        }
        return data;
    }
//==================================Public Methods==============================================
    @Override
    public void BeginTransaction(){
        AutoCommit=false;
    }
    @Override
    public void EndTransaction(){
        AutoCommit=true;
        flush();
    }
    @Override
    public void rollback(){
        saveQuery.clear();
    }
    @Override
    public void Commit(){
        flush();
    }
    @Override
    public TypeMap.Entry<String, String, String> Get(String key){
        return Read().get(key);
    }
    @Override
    public void Set(TypeMap.Entry<String,String,String> data){
        Write(data);
    }
    @Override
    public boolean Remove(String key){
        return RemoveEntity(key);
    }
    @Override
    public void InvalidateCache(){
        isCacheDirty=true;
    }
    @Override
    public TypeMap<String,String,String> query(boolean iKey,String keyReg,boolean iType,String typeReg,boolean iVal,String valReg){
        TypeMap<String,String,String> outData = new TypeMap<>();
        for (TypeMap.Entry<String,String,String> dd:Read().getEntryList()){
            if ((iKey^dd.getKey().matches(keyReg))&&(iType^dd.getValue1().matches(typeReg))&&(iVal^dd.getValue2().matches(valReg))){
                outData.put(dd);
            }
        }
        return outData;
    }
    @Override
    public boolean Backup(File path, boolean override){
        return converterInterface.Backup(path,override);
    }

    @Override
    public void RemoveAll() {
        saveQuery.clear();
        cache.clear();
        Interations=0;
        readInterations=0;
        flush();
        isCacheDirty=true;
    }
    @Override
    public boolean Exists(String key){
        return Read().containsKey(key);
    }
    @Override
    public List<String> getAllKeys(){
        return Read().getKeyList();
    }
    @Override
    public List<String> getAllKeys(String regx){
        return Read().getKeyList().stream().filter(string -> string.matches(regx)).collect(Collectors.toList());
    }
    @Override
    public String getTypeSimpleName(String key){
        if (!Exists(key)) return null;
        return Read().getValue1(key);
    }
}
