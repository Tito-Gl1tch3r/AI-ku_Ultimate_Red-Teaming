/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.ConverterInterface;
import com.codehack.JungleConfig.Core.IOHandlerInterface;
import com.codehack.JungleConfig.Core.JJacksonModule;
import com.codehack.JungleConfig.DataModel.TypeMap;
import com.fasterxml.jackson.core.type.TypeReference;
import java.io.File;

/**
 *
 * @author Himansa
 */
public class NativeFlatJsonConverter implements ConverterInterface{

    private IOHandlerInterface handler;

    public NativeFlatJsonConverter(IOHandlerInterface handler) {
        this.handler = handler;
    }
    
    @Override
    public TypeMap<String, String, String> decode() {
        return JJacksonModule.ConvertToObject(handler.Read(), new TypeReference<TypeMap<String,String,String>>() {});
    }

    @Override
    public void encode(TypeMap<String, String, String> data) {
        handler.Write(JJacksonModule.ConvertToJson(data));
    }

    @Override
    public boolean Backup(File path, boolean override) {
        return handler.Backup(path, override);
    }
}
