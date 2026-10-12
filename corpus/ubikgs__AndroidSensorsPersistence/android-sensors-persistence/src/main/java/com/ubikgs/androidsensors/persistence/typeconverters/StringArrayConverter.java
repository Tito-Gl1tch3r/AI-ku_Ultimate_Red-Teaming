package com.ubikgs.androidsensors.persistence.typeconverters;

import android.arch.persistence.room.TypeConverter;

import java.util.Arrays;

/**
 * Copyright 2017 Alberto González Pérez
 * <p>
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * <p>
 * <p>http://www.apache.org/licenses/LICENSE-2.0</p>
 * <p>
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

public class StringArrayConverter extends ArrayConverter {

    private static final String EMPTY_CHARACTER = "\\0";

    @TypeConverter
    public String serialize(String[] array) {
        if (array == null) return null;
        String[] escaped = stringArrayConverter(array, stringEscaper);
        return Arrays.toString(escaped);
    }

    @TypeConverter
    public String[] deserialize(String arrayAsString) {
        if (arrayAsString == null) return null;

        try {
            return parseArray(arrayAsString);
        } catch (Exception e) {
            return null;
        }
    }

    private String [] parseArray(String arrayAsString) {
        String[] stringParts = getStringParts(arrayAsString);
        String[] copy = stringArrayConverter(stringParts, stringUnescaper);
        return copy;
    }

    private String[] stringArrayConverter(String[] array, StringConverter stringConverter) {
        String[] copy = new String[array.length];
        for (int i = 0; i < array.length; i++) {
            copy[i] = stringConverter.convert(array[i]);
        }
        return copy;
    }

    private interface StringConverter {
        String convert(String string);
    }

    private static StringConverter stringEscaper = new StringConverter() {

        @Override
        public String convert(String string) {
            return string.equals("") ? EMPTY_CHARACTER : string;
        }
    };

    private static StringConverter stringUnescaper = new StringConverter() {

        @Override
        public String convert(String string) {
            return string.equals(EMPTY_CHARACTER) ? "" : string;
        }
    };
}
