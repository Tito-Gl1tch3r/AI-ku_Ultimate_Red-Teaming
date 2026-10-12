package com.ubikgs.androidsensors.persistence.entities.wifi;

import android.arch.persistence.room.Entity;
import android.arch.persistence.room.Index;
import android.arch.persistence.room.PrimaryKey;

import com.ubikgs.androidsensors.persistence.entities.RecordEntity;
import com.ubikgs.androidsensors.records.wifi.WifiMeasurementsRecord;

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

@Entity(indices = {@Index("foreignKey")})
public class WifiMeasurementsEntity extends WifiMeasurementsRecord
        implements RecordEntity<WifiMeasurementsRecord> {

    @PrimaryKey(autoGenerate = true)
    private long uid;

    private long foreignKey;

    public WifiMeasurementsEntity() {
        super();
    }

    public WifiMeasurementsEntity(WifiMeasurementsRecord wifiMeasurementsRecord) {
        super(wifiMeasurementsRecord);
    }

    @Override
    public long getUid() {
        return uid;
    }

    @Override
    public void setUid(long uid) {
        this.uid = uid;
    }

    @Override
    public long getForeignKey() {
        return foreignKey;
    }

    @Override
    public void setForeignKey(long foreignKey) {
        this.foreignKey = foreignKey;
    }

    @Override
    public WifiMeasurementsRecord toSensorRecord() {
        return new WifiMeasurementsRecord(this);
    }

    @Override
    public String toString() {
        return "WifiMeasurementsEntity{" +
                "uid=" + uid +
                ", foreignKey=" + foreignKey +
                "} " + super.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof WifiMeasurementsEntity)) return false;
        if (!super.equals(o)) return false;

        WifiMeasurementsEntity that = (WifiMeasurementsEntity) o;

        if (uid != that.uid) return false;
        return foreignKey == that.foreignKey;
    }

    @Override
    public int hashCode() {
        int result = super.hashCode();
        result = 31 * result + (int) (uid ^ (uid >>> 32));
        result = 31 * result + (int) (foreignKey ^ (foreignKey >>> 32));
        return result;
    }
}
