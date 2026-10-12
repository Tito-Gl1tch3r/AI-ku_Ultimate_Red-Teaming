package com.ubikgs.androidsensors.persistence.migrations;

import android.arch.persistence.db.SupportSQLiteDatabase;
import android.arch.persistence.room.migration.Migration;
import android.support.annotation.NonNull;

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

public class Migration1to2 extends Migration {

    @Inject
    public Migration1to2() {
        super(1, 2);
    }

    @Override
    public void migrate(@NonNull SupportSQLiteDatabase database) {
        database.execSQL("CREATE TABLE IF NOT EXISTS `WifiMeasurementsEntity` (" +
                "`uid` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                "`foreignKey` INTEGER NOT NULL, " +
                "`ssidCount` INTEGER NOT NULL, " +
                "`bssids` TEXT, " +
                "`ssids` TEXT, " +
                "`capabilities` TEXT, " +
                "`centerFreq0s` TEXT, " +
                "`centerFreq1s` TEXT, " +
                "`channelWidths` TEXT, " +
                "`frequencies` TEXT, " +
                "`levels` TEXT, " +
                "`operatorsFriendlyName` TEXT, " +
                "`timestamps` TEXT, " +
                "`venueNames` TEXT, " +
                "`accuracy` REAL NOT NULL, " +
                "`sensorTimestamp` INTEGER NOT NULL, " +
                "`systemTimestamp` INTEGER NOT NULL" +
            ")");
        database.execSQL("CREATE  INDEX `index_WifiMeasurementsEntity_foreignKey` " +
                "ON `WifiMeasurementsEntity` (`foreignKey`)");
    }
}
