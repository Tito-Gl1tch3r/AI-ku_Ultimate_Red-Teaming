package com.ubikgs.androidsensors.persistence.testutils;

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
import com.ubikgs.androidsensors.records.SensorRecord;
import com.ubikgs.androidsensors.records.gps.LocationRecord;
import com.ubikgs.androidsensors.records.gps.RawGPSMeasurementsRecord;
import com.ubikgs.androidsensors.records.gps.RawGPSNavigationRecord;
import com.ubikgs.androidsensors.records.gps.RawGPSStatusRecord;
import com.ubikgs.androidsensors.records.imu.AccelerometerRecord;
import com.ubikgs.androidsensors.records.imu.GravityRecord;
import com.ubikgs.androidsensors.records.imu.GyroscopeRecord;
import com.ubikgs.androidsensors.records.imu.LinearAccelerationRecord;
import com.ubikgs.androidsensors.records.imu.MagneticFieldRecord;
import com.ubikgs.androidsensors.records.imu.RotationVectorRecord;
import com.ubikgs.androidsensors.records.imu.TriAxisRecord;
import com.ubikgs.androidsensors.records.wifi.WifiMeasurementsRecord;

import java.util.Date;
import java.util.Random;

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

public class TestEntityProvider {

    private static Random random = new Random();

    public static AccelerometerEntity createAccelerometerRecordEntity() {
        AccelerometerEntity entity = new AccelerometerEntity();
        initializeSensorRecordFields(entity);
        initializeTriAxisRecordFields(entity);
        return entity;
    }

    public static GravityEntity createGravityRecordEntity() {
        GravityEntity entity = new GravityEntity();
        initializeSensorRecordFields(entity);
        initializeTriAxisRecordFields(entity);
        return entity;
    }

    public static GyroscopeEntity createGyroscopeRecordEntity() {
        GyroscopeEntity entity = new GyroscopeEntity();
        initializeSensorRecordFields(entity);
        initializeTriAxisRecordFields(entity);
        return entity;
    }

    public static LinearAccelerationEntity createLinearAccelerationRecordEntity() {
        LinearAccelerationEntity entity = new LinearAccelerationEntity();
        initializeSensorRecordFields(entity);
        initializeTriAxisRecordFields(entity);
        return entity;
    }

    public static MagneticFieldEntity createMagneticFieldRecordEntity() {
        MagneticFieldEntity entity = new MagneticFieldEntity();
        initializeSensorRecordFields(entity);
        initializeTriAxisRecordFields(entity);
        return entity;
    }

    public static RotationVectorEntity createRotationVectorRecordEntity() {
        RotationVectorEntity entity = new RotationVectorEntity();
        initializeSensorRecordFields(entity);
        entity.setXSin(random.nextFloat());
        entity.setYSin(random.nextFloat());
        entity.setZSin(random.nextFloat());
        entity.setCos(random.nextFloat());
        return entity;
    }

    public static LocationEntity createLocationRecordEntity() {
        LocationEntity entity = new LocationEntity();
        initializeSensorRecordFields(entity);
        entity.setLatitude(random.nextDouble());
        entity.setLongitude(random.nextDouble());
        entity.setAltitude(random.nextDouble());
        entity.setSpeed(random.nextFloat());
        entity.setBearing(random.nextFloat());
        return entity;
    }

    public static RawGPSMeasurementsEntity createRawGPSMeasurementsRecordEntity() {
        RawGPSMeasurementsEntity entity = new RawGPSMeasurementsEntity();
        initializeSensorRecordFields(entity);
        entity.setSatelliteCount(random.nextInt(3));
        entity.setSvids(generateRandomIntArray());
        entity.setConstellations(generateRandomIntArray());
        entity.setTimeOffsets(generateRandomDoubleArray());
        entity.setStateCodes(generateRandomIntArray());
        entity.setSvTimes(generateRandomLongArray());
        entity.setSvTimeUncerts(generateRandomLongArray());
        entity.setCn0DbHzs(generateRandomDoubleArray());
        entity.setPseudoranges(generateRandomDoubleArray());
        entity.setPseudorangeUncerts(generateRandomDoubleArray());
        entity.setDeltaStates(generateRandomIntArray());
        entity.setDeltas(generateRandomDoubleArray());
        entity.setDeltaUncerts(generateRandomDoubleArray());
        entity.setMultipaths(generateRandomIntArray());
        return entity;
    }

    public static RawGPSNavigationEntity createRawGPSNavigationRecordEntity() {
        RawGPSNavigationEntity entity = new RawGPSNavigationEntity();
        initializeSensorRecordFields(entity);
        entity.setAccuracy(random.nextFloat());
        entity.setSensorTimestamp(new Date().getTime());
        entity.setSystemTimestamp(new Date().getTime());
        entity.setMessage(new String(new char[255]));
        return entity;
    }

    public static RawGPSStatusEntity createRawGPSStatusRecordEntity() {
        RawGPSStatusEntity entity = new RawGPSStatusEntity();
        initializeSensorRecordFields(entity);
        entity.setAccuracy(random.nextFloat());
        entity.setSensorTimestamp(new Date().getTime());
        entity.setSystemTimestamp(new Date().getTime());
        entity.setSatelliteCount(random.nextInt(3));
        entity.setAzimuths(generateRandomFloatArray());
        entity.setCn0DHzs(generateRandomFloatArray());
        entity.setConstellationTypes(generateRandomIntArray());
        entity.setElevations(generateRandomFloatArray());
        entity.setSvids(generateRandomIntArray());
        return entity;
    }

    public static WifiMeasurementsEntity createWifiMeasurementsEntity() {
        WifiMeasurementsEntity entity = new WifiMeasurementsEntity();
        initializeSensorRecordFields(entity);
        entity.setSsidCount(random.nextInt());
        entity.setBssids(generateRandomStringArray());
        entity.setSsids(generateRandomStringArray());
        entity.setCapabilities(generateRandomStringArray());
        entity.setCenterFreq0s(generateRandomIntArray());
        entity.setCenterFreq1s(generateRandomIntArray());
        entity.setChannelWidths(generateRandomIntArray());
        entity.setFrequencies(generateRandomIntArray());
        entity.setLevels(generateRandomIntArray());
        entity.setOperatorsFriendlyName(generateRandomStringArray());
        entity.setTimestamps(generateRandomLongArray());
        entity.setVenueNames(generateRandomStringArray());
        return entity;
    }

    public static AccelerometerRecord createAccelerometerRecord() {
        return createAccelerometerRecordEntity().toSensorRecord();
    }

    public static GravityRecord createGravityRecord() {
        return createGravityRecordEntity().toSensorRecord();
    }

    public static GyroscopeRecord createGyroscopeRecord() {
        return createGyroscopeRecordEntity().toSensorRecord();
    }

    public static LinearAccelerationRecord createLinearAccelerationRecord() {
        return createLinearAccelerationRecordEntity().toSensorRecord();
    }

    public static MagneticFieldRecord createMagneticFieldRecord() {
        return createMagneticFieldRecordEntity().toSensorRecord();
    }

    public static RotationVectorRecord createRotationVectorRecord() {
        return createRotationVectorRecordEntity().toSensorRecord();
    }

    public static LocationRecord createLocationRecord() {
        return createLocationRecordEntity().toSensorRecord();
    }

    public static RawGPSMeasurementsRecord createRawGPSMeasurementsRecord() {
        return createRawGPSMeasurementsRecordEntity().toSensorRecord();
    }

    public static RawGPSNavigationRecord createRawGPSNavigationRecord() {
        return createRawGPSNavigationRecordEntity().toSensorRecord();
    }

    public static RawGPSStatusRecord createRawGPSStatusRecord() {
        return createRawGPSStatusRecordEntity().toSensorRecord();
    }

    public static WifiMeasurementsRecord createWifiMeasurementsRecord() {
        return createWifiMeasurementsEntity().toSensorRecord();
    }

    private static void initializeSensorRecordFields(SensorRecord sensorRecord) {
        sensorRecord.setAccuracy(random.nextFloat());
        sensorRecord.setSensorTimestamp(new Date().getTime());
        sensorRecord.setSystemTimestamp(new Date().getTime());
    }

    private static void initializeTriAxisRecordFields(TriAxisRecord triAxisRecord) {
        triAxisRecord.setX(random.nextFloat());
        triAxisRecord.setY(random.nextFloat());
        triAxisRecord.setZ(random.nextFloat());
    }

    private static double[] generateRandomDoubleArray() {
        double[] doubles = new double[generateRandomArrayLength()];
        for (int i = 0; i < doubles.length; i++) {
            doubles[i] = random.nextDouble();
        }
        return doubles;
    }

    private static float[] generateRandomFloatArray() {
        float[] floats = new float[generateRandomArrayLength()];
        for (int i = 0; i < floats.length; i++) {
            floats[i] = random.nextFloat();
        }
        return floats;
    }

    private static int[] generateRandomIntArray() {
        int[] ints = new int[generateRandomArrayLength()];
        for (int i = 0; i < ints.length; i++) {
            ints[i] = random.nextInt();
        }
        return ints;
    }

    private static long[] generateRandomLongArray() {
        long[] longs = new long[generateRandomArrayLength()];
        for (int i = 0; i < longs.length; i++) {
            longs[i] = random.nextLong();
        }
        return longs;
    }

    private static String[] generateRandomStringArray() {
        String[] strings = new String[generateRandomArrayLength()];
        for (int i = 0; i < strings.length; i++) {
            strings[i] = new String(new char[generateRandomArrayLength()])
                    .replace('\0', 'o');
        }
        return strings;
    }

    private static int generateRandomArrayLength() {
        return random.nextInt(3);
    }
}
