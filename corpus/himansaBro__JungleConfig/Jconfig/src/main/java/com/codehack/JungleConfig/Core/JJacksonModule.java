package com.codehack.JungleConfig.Core;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

public class JJacksonModule {
    public static ObjectMapper mapper=new ObjectMapper();
    private static boolean setuped;
    public static ObjectMapper getMapper(){
        if (!setuped){
            mapper.registerModule(new JavaTimeModule());
            mapper.registerModule(new Jdk8Module());
        }
        return mapper;
    }
    public static String ConvertToJson(Object data){
        try {
            return getMapper().writeValueAsString(data);
        } catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
    }
    public static <T> T ConvertToObject(String json,Class<T> type){
        try {
            return getMapper().readValue(json,type);
        } catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T ConvertToObject(String value2, TypeReference<T> type) {
        try {
            return getMapper().readValue(value2,type);
        } catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
    }
}
