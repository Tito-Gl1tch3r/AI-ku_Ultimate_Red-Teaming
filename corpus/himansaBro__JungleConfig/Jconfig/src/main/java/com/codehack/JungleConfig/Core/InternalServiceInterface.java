/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.codehack.JungleConfig.Core;

import com.codehack.JungleConfig.DataModel.TypeMap;
import java.io.File;
import java.util.List;

/**
 *
 * @author Himansa
 */
public interface InternalServiceInterface {
    void BeginTransaction();
    void EndTransaction();
    void Rollback();
    void Commit();

    TypeMap.Entry<String,String,String> Get(String key);
    void Set(TypeMap.Entry<String,String,String> data);
    boolean Remove(String key);
    void InvalidateCache();

    TypeMap<String,String,String> query(boolean iKey,String keyReg,boolean iType,String typeReg,boolean iVal,String valReg);

    void RemoveAll();

    boolean Exists(String key);

    List<String> getAllKeys();

    List<String> getAllKeys(String regx);

    String getTypeSimpleName(String key);
    boolean Backup(File file,boolean Override);
}
