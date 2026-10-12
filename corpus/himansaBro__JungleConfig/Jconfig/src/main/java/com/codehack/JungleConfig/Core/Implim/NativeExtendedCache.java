/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.CacheInterface;
import com.codehack.JungleConfig.Core.InternalServiceInterface;
import com.codehack.JungleConfig.DataModel.TypeMap;
import java.io.File;
import java.util.List;

/**
 *
 * @author Himansa
 */
public class NativeExtendedCache implements CacheInterface{

    private final InternalServiceInterface serviceInterface;

    public NativeExtendedCache(InternalServiceInterface serviceInterface) {
        this.serviceInterface = serviceInterface;
    }
    
    @Override
    public void BeginTransaction() {
        serviceInterface.BeginTransaction();
    }

    @Override
    public void EndTransaction() {
        serviceInterface.EndTransaction();
    }

    @Override
    public void rollback() {
        serviceInterface.Rollback();
    }

    @Override
    public void Commit() {
        serviceInterface.Commit();
    }

    @Override
    public TypeMap.Entry<String, String, String> Get(String key) {
        return serviceInterface.Get(key);
    }

    @Override
    public void Set(TypeMap.Entry<String, String, String> data) {
        serviceInterface.Set(data);
    }

    @Override
    public boolean Remove(String key) {
        return serviceInterface.Remove(key);
    }

    @Override
    public void InvalidateCache() {
        serviceInterface.InvalidateCache();
    }

    @Override
    public TypeMap<String, String, String> query(boolean iKey, String keyReg, boolean iType, String typeReg, boolean iVal, String valReg) {
        return serviceInterface.query(iKey, keyReg, iType, typeReg, iVal, valReg);
    }

    @Override
    public boolean Backup(File path, boolean override) {
        return serviceInterface.Backup(path, override);
    }

    @Override
    public void RemoveAll() {
        serviceInterface.RemoveAll();
    }

    @Override
    public boolean Exists(String key) {
        return serviceInterface.Exists(key);
    }

    @Override
    public List<String> getAllKeys() {
        return serviceInterface.getAllKeys();
    }

    @Override
    public List<String> getAllKeys(String regx) {
        return serviceInterface.getAllKeys(regx);
    }

    @Override
    public String getTypeSimpleName(String key) {
        return serviceInterface.getTypeSimpleName(key);
    }
    
}
