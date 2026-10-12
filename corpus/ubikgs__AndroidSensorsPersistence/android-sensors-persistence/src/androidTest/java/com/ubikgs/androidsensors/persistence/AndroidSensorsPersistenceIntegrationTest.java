package com.ubikgs.androidsensors.persistence;

import android.content.Context;

import com.ubikgs.androidsensors.SensorType;
import com.ubikgs.androidsensors.persistence.repositories.RecordRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.AccelerometerRepository;
import com.ubikgs.androidsensors.records.imu.AccelerometerRecord;

import org.junit.Before;
import org.junit.Test;

import javax.inject.Inject;

import static org.hamcrest.core.Is.is;
import static org.hamcrest.core.IsEqual.equalTo;
import static org.hamcrest.core.IsNot.not;
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
public class AndroidSensorsPersistenceIntegrationTest {

    private static final int REPOSITORY_COUNT = 11;

    @Inject Context context;

    private AndroidSensorsPersistence androidSensorsPersistence;

    @Before
    public void setUp() throws Exception {
        DaggerTestBedComponent.create().inject(this);

        androidSensorsPersistence = AndroidSensorsPersistence
                .builder()
                .build(context);
    }

    @Test
    public void recordRepositories_withDefaultConfigIsEmpty_isFalse() throws Exception {
        boolean empty = androidSensorsPersistence.allRecordRepositories().isEmpty();
        assertThat(empty, is(false));
    }

    @Test
    public void recordRepositories_withDefaultConfigEqualsRepositoryCount_isFalse() throws Exception {
        int count = androidSensorsPersistence.allRecordRepositories().size();
        assertThat(count, equalTo(REPOSITORY_COUNT));
    }

    @Test
    public void recordRepository_withDefaultConfig_returnsAccelerometerRepository() throws Exception {
        AccelerometerRepository accelerometerRepository =
                androidSensorsPersistence.recordRepository(AccelerometerRepository.class);

        assertThat(accelerometerRepository, not(equalTo(null)));
    }

    @Test
    public void recordRepositoryBySensorType_withDefaultConfig_returnsAccelerometerRepository() throws Exception {
        RecordRepository recordRepository =
                androidSensorsPersistence.recordRepositoryBy(SensorType.ACCELEROMETER);

        assertThat(recordRepository, not(equalTo(null)));
    }

    @Test
    public void recordRepositoryBySensorRecord_withDefaultConfic_returnsAccelerometerRepository() throws Exception {
        RecordRepository recordRepository =
                androidSensorsPersistence.recordRepositoryBy(AccelerometerRecord.class);

        assertThat(recordRepository, not(equalTo(null)));
    }
}