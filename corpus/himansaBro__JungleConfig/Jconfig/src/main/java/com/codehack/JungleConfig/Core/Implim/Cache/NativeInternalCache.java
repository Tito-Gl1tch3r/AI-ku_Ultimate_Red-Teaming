/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.codehack.JungleConfig.Core.Implim.Cache;

import com.codehack.JungleConfig.Core.ConverterInterface;
import com.codehack.JungleConfig.Core.InternalCacheInterface;
import com.codehack.JungleConfig.DataModel.TypeMap;
import java.io.File;
import java.util.List;

/**
 *
 * @author Himansa
 */
public class NativeInternalCache implements InternalCacheInterface {
    private ConverterInterface converter;
    private TypeMap<String, String, String> cache = new TypeMap<>();
    private int MAX_WRITES_MARGE;
    private int MAX_READS_MARGE;
    private int currentWrites;
    private int currentReads;
    private boolean isDirty;
    private boolean useCache;

    public NativeInternalCache(ConverterInterface converter, int MAX_WRITES_MARGE, int MAX_READS_MARGE,
            boolean useCache) {
        this.converter = converter;
        this.MAX_WRITES_MARGE = MAX_WRITES_MARGE;
        this.MAX_READS_MARGE = MAX_READS_MARGE;
        this.useCache = useCache;
    }

    private TypeMap<String, String, String> getCache() {
        if (!useCache)
            return converter.decode();
        if (isDirty || (currentReads > MAX_READS_MARGE) || (currentWrites > MAX_WRITES_MARGE)) {
            cache = converter.decode();
            isDirty = false;
            currentReads = 0;
            currentWrites = 0;
        }
        currentReads++;
        return cache;
    }

    private TypeMap<String, String, String> getUpdatedCache(TypeMap<String, String, String> saveQuery,
            List<String> remList) {
        TypeMap<String, String, String> tempCache = getCache();
        for (TypeMap.Entry<String, String, String> entry : saveQuery.getEntryList()) {
            tempCache.put(entry);
        }
        for (String string : remList) {
            tempCache.remove(string);
        }
        return tempCache;
    }

    @Override
    public void Set(TypeMap<String, String, String> saveQuery, List<String> remList) {
        converter.encode(getUpdatedCache(saveQuery, remList));
        currentWrites++;
    }

    @Override
    public TypeMap<String, String, String> Get(TypeMap<String, String, String> saveQuery, List<String> remList) {
        return getUpdatedCache(saveQuery, remList);
    }

    @Override
    public void Invalidate() {
        isDirty = true;
    }

    @Override
    public boolean Backup(File file, boolean override) {
        return converter.Backup(file, override);
    }
}
