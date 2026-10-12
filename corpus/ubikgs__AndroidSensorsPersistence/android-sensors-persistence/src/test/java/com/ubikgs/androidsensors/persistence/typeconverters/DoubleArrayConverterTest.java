package com.ubikgs.androidsensors.persistence.typeconverters;

import org.junit.Before;
import org.junit.Test;

import static org.hamcrest.core.Is.is;
import static org.hamcrest.core.IsEqual.equalTo;
import static org.junit.Assert.assertThat;

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
public class DoubleArrayConverterTest {
    private DoubleArrayConverter converter;

    @Before
    public void setUp() throws Exception {
        converter = new DoubleArrayConverter();
    }

    @Test
    public void serializeAndDeserialize_areReversible() throws Exception {
        double[] array = new double[]{0.0, 1.0, 2.0};

        String serialized = converter.serialize(array);
        double[] deserialized = converter.deserialize(serialized);

        assertThat(deserialized, equalTo(array));
    }

    @Test
    public void serialize_withNullInput_returnsNull() throws Exception {
        String serialized = converter.serialize(null);

        assertThat(serialized == null, is(true));
    }

    @Test
    public void deserialize_withNullInput_returnsNull() throws Exception {
        double[] deserialized = converter.deserialize(null);

        assertThat(deserialized == null, is(true));
    }

    @Test
    public void deserialized_withEmptyString_returnsNull() throws Exception {
        double[] deserialized = converter.deserialize("");

        assertThat(deserialized == null, is(true));
    }

    @Test
    public void deserialized_withEmptyArrayRepresentation_returnsEmptyArray() throws Exception {
        double[] deserialized = converter.deserialize("[]");

        assertThat(deserialized, equalTo(new double[]{}));
    }
}