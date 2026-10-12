package com.ubikgs.androidsensors.persistence.daos;

import android.arch.persistence.room.Insert;

import com.ubikgs.androidsensors.persistence.entities.RecordEntity;

import java.util.Collection;
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

public interface RecordEntityDao<T extends RecordEntity>  {
    @Insert
    List<Long> createAll(Collection<T> entities);

    Single<List<T>> findAll(long offset, long limit);

    Single<Long> count();

    Single<List<T>> findAllBy(long foreignKey, long offset, long limit);

    Single<Long> countBy(long foreignKey);

    void removeAll();

    void removeAllBy(long foreignKey);
}
