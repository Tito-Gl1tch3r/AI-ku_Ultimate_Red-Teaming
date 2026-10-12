package com.ubikgs.androidsensors.persistence.database;

import android.arch.persistence.room.Database;
import android.arch.persistence.room.RoomDatabase;
import android.arch.persistence.room.TypeConverters;

import com.ubikgs.androidsensors.persistence.daos.gps.LocationEntityDao;
import com.ubikgs.androidsensors.persistence.daos.gps.RawGPSMeasurementsEntityDao;
import com.ubikgs.androidsensors.persistence.daos.gps.RawGPSNavigationEntityDao;
import com.ubikgs.androidsensors.persistence.daos.gps.RawGPSStatusEntityDao;
import com.ubikgs.androidsensors.persistence.daos.imu.AccelerometerEntityDao;
import com.ubikgs.androidsensors.persistence.daos.imu.GravityEntityDao;
import com.ubikgs.androidsensors.persistence.daos.imu.GyroscopeEntityDao;
import com.ubikgs.androidsensors.persistence.daos.imu.LinearAccelerationEntityDao;
import com.ubikgs.androidsensors.persistence.daos.imu.MagneticFieldEntityDao;
import com.ubikgs.androidsensors.persistence.daos.imu.RotationVectorEntityDao;
import com.ubikgs.androidsensors.persistence.daos.wifi.WifiMeasurementsEntityDao;
import com.ubikgs.androidsensors.persistence.entities.gps.LocationEntity;
import com.ubikgs.androidsensors.persistence.entities.gps.RawGPSMeasurementsEntity;
import com.ubikgs.androidsensors.persistence.entities.gps.RawGPSNavigationEntity;
import com.ubikgs.androidsensors.persistence.entities.gps.RawGPSStatusEntity;
import com.ubikgs.androidsensors.persistence.entities.imu.AccelerometerEntity;
import com.ubikgs.androidsensors.persistence.entities.imu.GravityEntity;
import com.ubikgs.androidsensors.persistence.entities.imu.GyroscopeEntity;
import com.ubikgs.androidsensors.persistence.entities.imu.LinearAccelerationEntity;
import com.ubikgs.androidsensors.persistence.entities.imu.MagneticFieldEntity;
import com.ubikgs.androidsensors.persistence.entities.imu.RotationVectorEntity;
import com.ubikgs.androidsensors.persistence.entities.wifi.WifiMeasurementsEntity;
import com.ubikgs.androidsensors.persistence.typeconverters.DoubleArrayConverter;
import com.ubikgs.androidsensors.persistence.typeconverters.FloatArrayConverter;
import com.ubikgs.androidsensors.persistence.typeconverters.IntArrayConverter;
import com.ubikgs.androidsensors.persistence.typeconverters.LongArrayConverter;
import com.ubikgs.androidsensors.persistence.typeconverters.StringArrayConverter;

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
@Database(entities = {
        AccelerometerEntity.class,
        GravityEntity.class,
        GyroscopeEntity.class,
        LinearAccelerationEntity.class,
        MagneticFieldEntity.class,
        RotationVectorEntity.class,
        LocationEntity.class,
        RawGPSMeasurementsEntity.class,
        RawGPSNavigationEntity.class,
        RawGPSStatusEntity.class,
        WifiMeasurementsEntity.class
}, version = 2)
@TypeConverters({
        DoubleArrayConverter.class,
        FloatArrayConverter.class,
        IntArrayConverter.class,
        LongArrayConverter.class,
        StringArrayConverter.class
})
public abstract class AndroidSensorsDatabase extends RoomDatabase {
    /*
    * WARNING! If you modify this class or a linked entity remember to add and test a proper
    * database version migration.
    *
    * If you don't do so the sensors database will be wiped on every application using this library
    * */

    public abstract AccelerometerEntityDao accelerometerEntityDao();

    public abstract GravityEntityDao gravityEntityDao();

    public abstract GyroscopeEntityDao gyroscopeEntityDao();

    public abstract LinearAccelerationEntityDao linearAccelerationEntityDao();

    public abstract MagneticFieldEntityDao magneticFieldEntityDao();

    public abstract RotationVectorEntityDao rotationVectorEntityDao();

    public abstract LocationEntityDao locationEntityDao();

    public abstract RawGPSMeasurementsEntityDao rawGPSMeasurementsEntityDao();

    public abstract RawGPSNavigationEntityDao rawGPSNavigationEntityDao();

    public abstract RawGPSStatusEntityDao rawGPSStatusEntityDao();

    public abstract WifiMeasurementsEntityDao wifiMeasurementsEntityDao();
}
