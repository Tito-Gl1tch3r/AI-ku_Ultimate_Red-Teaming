package com.codehack.JungleConfig.Core.Implim.Converter;

import com.codehack.JungleConfig.Core.ConverterInterface;
import com.codehack.JungleConfig.Core.IOHandlerInterface;
import com.codehack.JungleConfig.DataModel.TypeMap;
import com.codehack.JungleConfig.Exceptions.InvalidConfigFormatException;

import java.io.File;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

public class NativeConverter implements ConverterInterface {
    private IOHandlerInterface handler;

    public NativeConverter(IOHandlerInterface handler) {
        this.handler = handler;
    }

    @Override
    public TypeMap<String, String, String> decode() {
        String data = handler.Read();
        data = preProcess(data);
        TypeMap<String, String, String> dataMap = new TypeMap<>();
        if (data.isBlank())
            return new TypeMap<String, String, String>();
        if (!data.startsWith("JConfig001"))
            throw new InvalidConfigFormatException();
        data = data.substring(data.indexOf("\n"));

        String[] dats = data.split("\n");
        for (String dat : dats) {
            if (!dat.strip().isBlank()) {
                int keySepIndex, ValSepIndex;
                keySepIndex = dat.indexOf(":");
                ValSepIndex = dat.indexOf("=");
                String key = dat.substring(0, keySepIndex);
                String type = dat.substring(keySepIndex + 1, ValSepIndex);
                String value = dat.substring(ValSepIndex).replaceFirst("=", "");
                dataMap.put(key, type, URLDecoder.decode(value, StandardCharsets.UTF_8));
            }
        }
        return dataMap;
    }

    protected String preProcess(String data) {
        return data;
    }

    @Override
    public void encode(TypeMap<String, String, String> data) {
        StringBuilder builder = new StringBuilder("JConfig001\n");
        for (TypeMap.Entry<String, String, String> dt : data.getEntryList()) {
            StringBuilder sb = new StringBuilder();
            validateKeys(dt.getKey());
            sb.append(dt.getKey()).append(":").append(dt.getValue1()).append("=")
                    .append(URLEncoder.encode(dt.getValue2(), StandardCharsets.UTF_8));
            builder.append(sb).append("\n");
        }
        handler.Write(preWrite(builder.toString()));
    }

    protected String preWrite(String data) {
        return data;
    }

    private void validateKeys(String key) {
        if (key.contains("\n") || key.contains(":") || key.contains("="))
            throw new IllegalArgumentException("Key's can't contain ':' '=' '\\n' ");
    }

    @Override
    public boolean Backup(File path, boolean override) {
        return handler.Backup(path, override);
    }
}
