package com.ubikgs.androidsensors.persistence.daos.gps;

import android.arch.persistence.room.Dao;
import android.arch.persistence.room.Query;

import com.ubikgs.androidsensors.persistence.daos.RecordEntityDao;
import com.ubikgs.androidsensors.persistence.entities.gps.RawGPSMeasurementsEntity;

import java.util.List;

import io.reactivex.Single;

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
@Dao
public interface RawGPSMeasurementsEntityDao extends RecordEntityDao<RawGPSMeasurementsEntity> {
    @Query("SELECT * FROM RawGPSMeasurementsEntity LIMIT :limit OFFSET :offset")
    Single<List<RawGPSMeasurementsEntity>> findAll(long offset, long limit);

    @Query("SELECT COUNT(*) FROM RawGPSMeasurementsEntity")
    Single<Long> count();

    @Query("SELECT * FROM RawGPSMeasurementsEntity WHERE foreignKey = :foreignKey LIMIT :limit OFFSET :offset")
    Single<List<RawGPSMeasurementsEntity>> findAllBy(long foreignKey, long offset, long limit);

    @Query("SELECT COUNT(*) FROM RawGPSMeasurementsEntity WHERE foreignKey = :foreignKey")
    Single<Long> countBy(long foreignKey);

    @Query("DELETE FROM RawGPSMeasurementsEntity")
    void removeAll();

    @Query("DELETE FROM RawGPSMeasurementsEntity WHERE foreignKey = :foreignKey")
    void removeAllBy(long foreignKey);
}
