package com.ubikgs.androidsensors.persistence.daos.gps;

import android.arch.persistence.room.Dao;
import android.arch.persistence.room.Query;

import com.ubikgs.androidsensors.persistence.daos.RecordEntityDao;
import com.ubikgs.androidsensors.persistence.entities.gps.RawGPSStatusEntity;

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
public interface RawGPSStatusEntityDao extends RecordEntityDao<RawGPSStatusEntity> {
    @Query("SELECT * FROM RawGPSStatusEntity LIMIT :limit OFFSET :offset")
    Single<List<RawGPSStatusEntity>> findAll(long offset, long limit);

    @Query("SELECT COUNT(*) FROM RawGPSStatusEntity")
    Single<Long> count();

    @Query("SELECT * FROM RawGPSStatusEntity WHERE foreignKey = :foreignKey LIMIT :limit OFFSET :offset")
    Single<List<RawGPSStatusEntity>> findAllBy(long foreignKey, long offset, long limit);

    @Query("SELECT COUNT(*) FROM RawGPSStatusEntity WHERE foreignKey = :foreignKey")
    Single<Long> countBy(long foreignKey);

    @Query("DELETE FROM RawGPSStatusEntity")
    void removeAll();

    @Query("DELETE FROM RawGPSStatusEntity WHERE foreignKey = :foreignKey")
    void removeAllBy(long foreignKey);
}
