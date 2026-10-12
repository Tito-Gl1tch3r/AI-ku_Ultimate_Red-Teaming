/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.InternalCacheInterface;
import com.codehack.JungleConfig.Core.InternalServiceInterface;
import com.codehack.JungleConfig.DataModel.TypeMap;
import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 *
 * @author Himansa
 */
public class NativeInternalTransaction implements InternalServiceInterface{
    private InternalCacheInterface cacheInterface;
    private TypeMap<String,String,String> saveQuery = new TypeMap<>();
    private List<String> remList = new ArrayList<>();
    private boolean AutoCommit;

    public NativeInternalTransaction(InternalCacheInterface cacheInterface) {
        this.cacheInterface = cacheInterface;    }
    
    
    private void send(){
        if (AutoCommit) {
            flush();
        }
    }
    private void flush(){
        cacheInterface.Set(saveQuery, remList);
        remList.clear();
        saveQuery.clear();
    }
    @Override
    public void BeginTransaction(){
        AutoCommit=false;
    }
    @Override
    public void EndTransaction(){
        AutoCommit=true;
        send();
    }
    @Override
    public void Commit(){
        flush();
    }
    @Override
    public void Rollback(){
        remList.clear();
        saveQuery.clear();
    }
    @Override
    public void Set(TypeMap.Entry<String,String,String> data){
        saveQuery.put(data);
        remList.remove(data.getKey());
        send();
    }
    @Override
    public TypeMap.Entry<String,String,String> Get(String key){
        return cacheInterface.Get(saveQuery, remList).get(key);
    }
    @Override
    public boolean Remove(String key){
        boolean validity = Get(key)!=null;
        saveQuery.remove(key);
        remList.add(key);
        send();
        return validity;
    }
    @Override
    public TypeMap<String,String,String> query(boolean iKey,String keyReg,boolean iType,String typeReg,boolean iVal,String valReg){
        TypeMap<String,String,String> outData = new TypeMap<>();
        for (TypeMap.Entry<String,String,String> dd:cacheInterface.Get(saveQuery, remList).getEntryList()){
            if ((iKey^dd.getKey().matches(keyReg))&&(iType^dd.getValue1().matches(typeReg))&&(iVal^dd.getValue2().matches(valReg))){
                outData.put(dd);
            }
        }
        return outData;
    }
    @Override
    public void RemoveAll(){
        List<String> tempRemList = cacheInterface.Get(saveQuery, remList).getKeyList();
        for (String string : tempRemList) {
            if (!remList.contains(string)) {
                remList.add(string);
            }
        }
        saveQuery.clear();
        send();
    }
    @Override
    public boolean Exists(String key){
        return (Get(key)!=null);
    }
    @Override
    public List<String> getAllKeys(){
        return cacheInterface.Get(saveQuery, remList).getKeyList();
    }
    @Override
    public List<String> getAllKeys(String regx){
        return getAllKeys().stream().filter(string -> string.matches(regx)).collect(Collectors.toList());
    }
    @Override
    public String getTypeSimpleName(String key){
        TypeMap.Entry<String,String,String> et = Get(key);
        if (et==null)return null;
        return et.getValue1();
    }
    @Override
    public void InvalidateCache(){
        cacheInterface.Invalidate();
    }

    @Override
    public boolean Backup(File file, boolean Override) {
        return cacheInterface.Backup(file, Override);
    }
}
