package com.ubikgs.androidsensors.persistence;

import com.ubikgs.androidsensors.SensorType;

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

public class RepositoryNotAvailableException extends RuntimeException {

    public RepositoryNotAvailableException(Class<?> type) {
        super(String.format("There is no repository available for %s", type.getSimpleName()));
    }

    public RepositoryNotAvailableException(SensorType sensorType) {
        super(String.format("%s has no repository", sensorType.name()));
    }
}
