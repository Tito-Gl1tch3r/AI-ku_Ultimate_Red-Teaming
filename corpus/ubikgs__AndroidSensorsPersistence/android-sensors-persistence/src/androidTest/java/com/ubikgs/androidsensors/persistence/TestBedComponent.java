package com.ubikgs.androidsensors.persistence;

import com.ubikgs.androidsensors.persistence.daos.gps.LocationEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.gps.RawGPSMeasurementsEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.gps.RawGPSNavigationEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.gps.RawGPSStatusEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.imu.AccelerometerEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.imu.GravityEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.imu.GyroscopeEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.imu.LinearAccelerationEntityDaoTest;
import com.ubikgs.androidsensors.persistence.daos.imu.MagneticFieldEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.imu.RotationVectorEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.daos.wifi.WifiMeasurementsEntityDaoIntegrationTest;
import com.ubikgs.androidsensors.persistence.migrations.MigrationTest;
import com.ubikgs.androidsensors.persistence.modules.AndroidSensorsPersistenceDaoModule;
import com.ubikgs.androidsensors.persistence.modules.TestBedModule;
import com.ubikgs.androidsensors.persistence.modules.TestConfigModule;
import com.ubikgs.androidsensors.persistence.repositories.gps.LocationRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.gps.RawGPSMeasurementsRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.gps.RawGPSNavigationRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.gps.RawGPSStatusRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.imu.AccelerometerRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.imu.GravityRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.imu.GyroscopeRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.imu.LinearAccelerationRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.imu.MagneticFieldRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.imu.RotationVectorRepositoryIntegrationTest;
import com.ubikgs.androidsensors.persistence.repositories.wifi.WifiMeasurementsRepositoryIntegrationTest;

import javax.inject.Singleton;

import dagger.Component;

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
@Singleton
@Component(modules = {
        TestBedModule.class,
        TestConfigModule.class,
        AndroidSensorsPersistenceDaoModule.class
})
public interface TestBedComponent {
    void inject(AccelerometerEntityDaoIntegrationTest test);

    void inject(GravityEntityDaoIntegrationTest test);

    void inject(GyroscopeEntityDaoIntegrationTest test);

    void inject(LinearAccelerationEntityDaoTest test);

    void inject(MagneticFieldEntityDaoIntegrationTest test);

    void inject(RotationVectorEntityDaoIntegrationTest test);

    void inject(LocationEntityDaoIntegrationTest test);

    void inject(RawGPSMeasurementsEntityDaoIntegrationTest test);

    void inject(RawGPSNavigationEntityDaoIntegrationTest test);

    void inject(RawGPSStatusEntityDaoIntegrationTest test);

    void inject(AccelerometerRepositoryIntegrationTest test);

    void inject(GravityRepositoryIntegrationTest test);

    void inject(GyroscopeRepositoryIntegrationTest test);

    void inject(LinearAccelerationRepositoryIntegrationTest test);

    void inject(MagneticFieldRepositoryIntegrationTest test);

    void inject(RotationVectorRepositoryIntegrationTest test);

    void inject(LocationRepositoryIntegrationTest test);

    void inject(RawGPSMeasurementsRepositoryIntegrationTest test);

    void inject(RawGPSNavigationRepositoryIntegrationTest test);

    void inject(RawGPSStatusRepositoryIntegrationTest test);

    void inject(AndroidSensorsPersistenceIntegrationTest test);

    void inject(WifiMeasurementsEntityDaoIntegrationTest test);

    void inject(MigrationTest test);

    void inject(WifiMeasurementsRepositoryIntegrationTest test);
}
