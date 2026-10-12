package com.ubikgs.androidsensors.persistence.migrations;

import android.arch.persistence.db.SupportSQLiteDatabase;
import android.arch.persistence.db.framework.FrameworkSQLiteOpenHelperFactory;
import android.arch.persistence.room.testing.MigrationTestHelper;
import android.content.Context;
import android.support.test.InstrumentationRegistry;

import com.ubikgs.androidsensors.persistence.DaggerTestBedComponent;
import com.ubikgs.androidsensors.persistence.database.AndroidSensorsDatabase;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.Test;

import javax.inject.Inject;
import javax.inject.Named;

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

public class MigrationTest {
    @Inject @Named("sensorsDBName") String dbName;
    @Inject Migration1to2 MIGRATION_1_2;
    @Inject Context context;

    @Rule public MigrationTestHelper helper = new MigrationTestHelper(
            InstrumentationRegistry.getInstrumentation(),
            AndroidSensorsDatabase.class.getCanonicalName(),
            new FrameworkSQLiteOpenHelperFactory());

    @Before
    public void setUp() throws Exception {
        DaggerTestBedComponent.create().inject(this);
    }

    @Ignore // Has been tested with a different mechanism
    @Test
    public void migrate1To2() throws Exception {
        SupportSQLiteDatabase db = helper.createDatabase(dbName, 1);

        db.close();

        helper.runMigrationsAndValidate(dbName, 2, true, MIGRATION_1_2);
    }
}
