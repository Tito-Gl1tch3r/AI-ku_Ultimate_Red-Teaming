package com.ubikgs.androidsensors.persistence;

import android.content.Context;

import com.ubikgs.androidsensors.SensorType;
import com.ubikgs.androidsensors.modules.AndroidSystemModule;
import com.ubikgs.androidsensors.persistence.modules.AndroidSensorsPersistenceConfigModule;
import com.ubikgs.androidsensors.persistence.repositories.RecordRepository;
import com.ubikgs.androidsensors.records.SensorRecord;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

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

public class AndroidSensorsPersistence {


    @Inject Set<RecordRepository> recordRepositories;

    private final Map<Class<? extends RecordRepository>, RecordRepository> mappedRepositoriesByClass;
    private final Map<SensorType, RecordRepository> mappedRepositoriesByType;
    private final Map<Class<? extends SensorRecord>,RecordRepository> mappedRepositoriesByRecordClass;

    private AndroidSensorsPersistence(Context context, String sensorsDBName) {

        this.mappedRepositoriesByClass = new HashMap<>();
        this.mappedRepositoriesByType = new HashMap<>();
        this.mappedRepositoriesByRecordClass = new HashMap<>();

        DaggerAndroidSensorsPersistenceComponent.builder()
                .androidSystemModule(new AndroidSystemModule(context))
                .androidSensorsPersistenceConfigModule(
                        new AndroidSensorsPersistenceConfigModule(sensorsDBName))
                .build()
                .inject(this);

        createRepositoriesMap();
    }

    private void createRepositoriesMap() {
        for (RecordRepository repository : recordRepositories) {
            mappedRepositoriesByClass.put(repository.getClass(), repository);
            mappedRepositoriesByType.put(repository.getSensorType(), repository);
            mappedRepositoriesByRecordClass.put(
                    repository.getSensorType().getRecordClass(), repository
            );
        }
    }

    public Set<RecordRepository> allRecordRepositories() {
        return new HashSet<>(recordRepositories);
    }

    @SuppressWarnings("unchecked")
    public <T extends RecordRepository> T recordRepository(Class<T> type) {
        if (!mappedRepositoriesByClass.containsKey(type))
            throw new RepositoryNotAvailableException(type);

        return (T) mappedRepositoriesByClass.get(type);
    }

    public RecordRepository recordRepositoryBy(SensorType sensorType) {
        if (!mappedRepositoriesByType.containsKey(sensorType))
            throw new RepositoryNotAvailableException(sensorType);

        return mappedRepositoriesByType.get(sensorType);
    }

    public <T extends SensorRecord> RecordRepository recordRepositoryBy(Class<T> recordClass) {
        if (!mappedRepositoriesByRecordClass.containsKey(recordClass))
            throw new RepositoryNotAvailableException(recordClass);

        return mappedRepositoriesByRecordClass.get(recordClass);
    }

    /*
    * Builder
    * */

    public interface Builder {
        Builder customSensorsDBName(String sensorsDBName);
        AndroidSensorsPersistence build(Context applicationContext);
    }

    public static Builder builder() {

        return new Builder() {

            private String sensorsDBName;

            @Override
            public Builder customSensorsDBName(String sensorsDBName) {
                this.sensorsDBName = sensorsDBName;
                return this;
            }

            @Override
            public AndroidSensorsPersistence build(Context applicationContext) {
                return new AndroidSensorsPersistence(applicationContext, sensorsDBName);
            }
        };
    }
}
