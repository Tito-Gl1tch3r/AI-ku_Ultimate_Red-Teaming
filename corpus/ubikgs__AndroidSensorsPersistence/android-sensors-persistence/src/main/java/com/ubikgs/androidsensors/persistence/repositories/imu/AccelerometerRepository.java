package com.ubikgs.androidsensors.persistence.repositories.imu;

import com.ubikgs.androidsensors.SensorType;
import com.ubikgs.androidsensors.persistence.daos.imu.AccelerometerEntityDao;
import com.ubikgs.androidsensors.persistence.entities.imu.AccelerometerEntity;
import com.ubikgs.androidsensors.persistence.repositories.AbstractRecordRepository;
import com.ubikgs.androidsensors.records.imu.AccelerometerRecord;

import javax.inject.Inject;

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

public class AccelerometerRepository extends AbstractRecordRepository<AccelerometerRecord, AccelerometerEntity> {

    @Inject
    public AccelerometerRepository(AccelerometerEntityDao sensorRecordEntityDao) {
        super(sensorRecordEntityDao);
    }

    @Override
    protected AccelerometerEntity createFrom(AccelerometerRecord sensorRecord) {
        return new AccelerometerEntity(sensorRecord);
    }

    @Override
    protected AccelerometerRecord transformIn(AccelerometerEntity entity) {
        return entity.toSensorRecord();
    }

    @Override
    public SensorType getSensorType() {
        return SensorType.ACCELEROMETER;
    }
}
