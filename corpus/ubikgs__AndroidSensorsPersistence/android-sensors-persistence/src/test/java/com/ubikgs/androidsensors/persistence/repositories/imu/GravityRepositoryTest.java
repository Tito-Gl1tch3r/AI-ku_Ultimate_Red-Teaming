package com.ubikgs.androidsensors.persistence.repositories.imu;

import com.ubikgs.androidsensors.persistence.daos.imu.GravityEntityDao;
import com.ubikgs.androidsensors.persistence.entities.imu.GravityEntity;
import com.ubikgs.androidsensors.persistence.repositories.RecordRepositoryTest;
import com.ubikgs.androidsensors.records.imu.GravityRecord;

import org.junit.Before;
import org.mockito.Mock;

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
public class GravityRepositoryTest
        extends RecordRepositoryTest<GravityRecord, GravityEntity> {

    @Mock
    GravityEntityDao gravityEntityDao;

    @Before
    public void setUp() throws Exception {
        recordEntityDao = gravityEntityDao;

        sensorRecordRepository = new GravityRepository(gravityEntityDao);
    }

    @Override
    protected GravityRecord createSensorRecord() {
        return new GravityRecord();
    }

    @Override
    protected GravityEntity createSensorRecordEntity() {
        return new GravityEntity();
    }


}