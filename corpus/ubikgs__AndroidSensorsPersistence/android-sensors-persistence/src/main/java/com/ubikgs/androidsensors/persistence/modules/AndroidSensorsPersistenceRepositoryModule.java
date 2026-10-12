package com.ubikgs.androidsensors.persistence.modules;

import com.ubikgs.androidsensors.persistence.repositories.RecordRepository;
import com.ubikgs.androidsensors.persistence.repositories.gps.LocationRepository;
import com.ubikgs.androidsensors.persistence.repositories.gps.RawGPSMeasurementsRepository;
import com.ubikgs.androidsensors.persistence.repositories.gps.RawGPSNavigationRepository;
import com.ubikgs.androidsensors.persistence.repositories.gps.RawGPSStatusRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.AccelerometerRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.GravityRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.GyroscopeRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.LinearAccelerationRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.MagneticFieldRepository;
import com.ubikgs.androidsensors.persistence.repositories.imu.RotationVectorRepository;
import com.ubikgs.androidsensors.persistence.repositories.wifi.WifiMeasurementsRepository;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import dagger.Module;
import dagger.Provides;
import dagger.multibindings.ElementsIntoSet;

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
@Module
public class AndroidSensorsPersistenceRepositoryModule {

    @Provides
    @ElementsIntoSet
    Set<RecordRepository> provideAllSensorRecordRepositories(
            AccelerometerRepository accelerometerRepository,
            GravityRepository gravityRepository,
            GyroscopeRepository gyroscopeRepository,
            LinearAccelerationRepository linearAccelerationRepository,
            MagneticFieldRepository magneticFieldRepository,
            RotationVectorRepository rotationVectorRepository,
            LocationRepository locationRepository,
            RawGPSMeasurementsRepository rawGPSMeasurementsRepository,
            RawGPSNavigationRepository rawGPSNavigationRepository,
            RawGPSStatusRepository rawGPSStatusRepository,
            WifiMeasurementsRepository wifiMeasurementsRepository) {

        return new HashSet<RecordRepository>(Arrays.asList(
                accelerometerRepository,
                gravityRepository,
                gyroscopeRepository,
                linearAccelerationRepository,
                magneticFieldRepository,
                rotationVectorRepository,
                locationRepository,
                rawGPSMeasurementsRepository,
                rawGPSNavigationRepository,
                rawGPSStatusRepository,
                wifiMeasurementsRepository));
    }
}
