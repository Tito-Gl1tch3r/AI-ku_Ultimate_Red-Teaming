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

public class IntArrayConverter extends ArrayConverter {

    @TypeConverter
    public String serialize(int[] array) {
        if (array == null) return null;
        return Arrays.toString(array);
    }

    @TypeConverter
    public int[] deserialize(String arrayAsString) {
        if (arrayAsString == null) return null;

        try {
            return parseArray(arrayAsString);
        } catch (Exception e) {
            return null;
        }
    }

    private int[] parseArray(String arrayAsString) {
        String[] parts = getStringParts(arrayAsString);

        int[] array = new int[parts.length];

        for (int i = 0; i < parts.length; i++) {
            array[i] = Integer.parseInt(parts[i]);
        }

        return array;
    }
}
