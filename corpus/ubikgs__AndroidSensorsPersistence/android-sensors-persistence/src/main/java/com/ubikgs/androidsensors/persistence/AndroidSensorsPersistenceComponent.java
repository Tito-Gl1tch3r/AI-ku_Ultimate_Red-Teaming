package com.ubikgs.androidsensors.persistence;

import com.ubikgs.androidsensors.modules.AndroidSystemModule;
import com.ubikgs.androidsensors.persistence.modules.AndroidSensorsPersistenceConfigModule;
import com.ubikgs.androidsensors.persistence.modules.AndroidSensorsPersistenceDaoModule;
import com.ubikgs.androidsensors.persistence.modules.AndroidSensorsPersistenceRepositoryModule;

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
        AndroidSystemModule.class,
        AndroidSensorsPersistenceConfigModule.class,
        AndroidSensorsPersistenceDaoModule.class,
        AndroidSensorsPersistenceRepositoryModule.class
})
public interface AndroidSensorsPersistenceComponent {

    @Component.Builder
    interface Builder {
        Builder androidSystemModule(AndroidSystemModule androidSystemModule);
        Builder androidSensorsPersistenceConfigModule(AndroidSensorsPersistenceConfigModule androidSensorsPersistenceConfigModule);
        AndroidSensorsPersistenceComponent build();
    }

    void inject(AndroidSensorsPersistence androidSensorsPersistence);
}
