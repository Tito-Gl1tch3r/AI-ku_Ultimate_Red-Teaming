package com.ubikgs.androidsensors.persistence.repositories;

import com.ubikgs.androidsensors.persistence.daos.RecordEntityDao;
import com.ubikgs.androidsensors.persistence.entities.RecordEntity;
import com.ubikgs.androidsensors.persistence.repositories.common.FindBucket;
import com.ubikgs.androidsensors.records.SensorRecord;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentMatchers;
import org.mockito.junit.MockitoJUnitRunner;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import io.reactivex.Single;

import static org.hamcrest.core.IsEqual.equalTo;
import static org.junit.Assert.assertThat;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

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
@RunWith(MockitoJUnitRunner.class)
public abstract class RecordRepositoryTest<T extends SensorRecord, E extends RecordEntity<T>> {


    protected RecordEntityDao<E> recordEntityDao;

    protected AbstractRecordRepository<T, E> sensorRecordRepository;

    public void setUp() throws Exception {
        if (recordEntityDao == null) {
            throw new Error("You must inject an instance of RecordEntityDao in setUp() method");
        }

        if (sensorRecordRepository == null) {
            throw new Error("You must inject an instance of RecordRepository in setUp() method");
        }
    }

    @Test
    public void createAll() throws Exception {
        Map<Long, T> recordsToCreate = provideSensorRecordsToCreate();

        List<Long> pKeys = new ArrayList<>(recordsToCreate.keySet());
        when(recordEntityDao.createAll(ArgumentMatchers.<E>anyCollection()))
                .thenReturn(pKeys);

        List<Long> keys = sensorRecordRepository.createAll(
                provideSensorRecordsToCreate().values()).blockingGet();

        verify(recordEntityDao, times(1)).createAll(ArgumentMatchers.<E>anyCollection());

        assertThat(keys, equalTo(pKeys));
    }

    @Test
    public void createAll_withForeignKey() throws Exception {
        Map<Long, T> recordsToCreate = provideSensorRecordsToCreate();

        List<Long> pKeys = new ArrayList<>(recordsToCreate.keySet());
        when(recordEntityDao.createAll(ArgumentMatchers.<E>anyCollection()))
                .thenReturn(pKeys);

        List<Long> keys = sensorRecordRepository.createAll(
                provideSensorRecordsToCreate().values(), 0L).blockingGet();

        verify(recordEntityDao, times(1)).createAll(ArgumentMatchers.<E>anyCollection());

        assertThat(keys, equalTo(pKeys));
    }

    @Test
    public void findAll() throws Exception {
        int count = 1001;

        List<T> sensorRecords =
                createSensorRecords(count);

        List<E> sensorRecordEntities =
                createSensorRecordEntities(count);

        when(recordEntityDao.count()).thenReturn(Single.just((long) count));
        when(recordEntityDao.findAll(0, 1000))
                .thenReturn(Single.just(sensorRecordEntities.subList(0, 1000)));
        when(recordEntityDao.findAll(1000, 1))
                .thenReturn(Single.just(sensorRecordEntities.subList(1000, 1001)));

        List<T> fetchedRecords = sensorRecordRepository.findAll()
                .toList()
                .blockingGet();

        assertThat(fetchedRecords.size(), equalTo(sensorRecords.size()));
    }

    @Test
    public void count() throws Exception {
        sensorRecordRepository.count();

        verify(recordEntityDao, times(1)).count();
    }

    @Test
    public void removeAll() throws Exception {
        sensorRecordRepository.removeAll();

        verify(recordEntityDao, times(1)).removeAll();
    }

    @Test
    public void findAllByForeignKey() throws Exception {
        int count = 1001;

        List<T> sensorRecords =
                createSensorRecords(count);

        List<E> sensorRecordEntities =
                createSensorRecordEntities(count);

        int foreignKey = 0;
        when(recordEntityDao.countBy(foreignKey)).thenReturn(Single.just((long) count));
        when(recordEntityDao.findAllBy(foreignKey, 0, 1000))
                .thenReturn(Single.just(sensorRecordEntities.subList(foreignKey, 1000)));
        when(recordEntityDao.findAllBy(foreignKey,1000, 1))
                .thenReturn(Single.just(sensorRecordEntities.subList(1000, 1001)));

        List<T> fetchedRecords = sensorRecordRepository.findAllBy(foreignKey)
                .toList()
                .blockingGet();

        assertThat(fetchedRecords.size(), equalTo(sensorRecords.size()));
    }

    @Test
    public void countByForeignKey() throws Exception {
        sensorRecordRepository.countBy(0L);

        verify(recordEntityDao, times(1)).countBy(0L);
    }

    @Test
    public void removeAllByForeignKey() throws Exception {
        sensorRecordRepository.removeAllBy(0L);

        verify(recordEntityDao, times(1)).removeAllBy(0L);
    }

    @Test
    public void createFindBucketsFrom_withRecordCountUnderLimit_returnsOneFindBucket() throws Exception {
        List<FindBucket> findBuckets =
                sensorRecordRepository.createFindBucketsFrom(999);

        assertThat(findBuckets.size(), equalTo(1));
        assertThat(findBuckets.get(0).getOffset(), equalTo(0L));
        assertThat(findBuckets.get(0).getLimit(), equalTo(999L));
    }

    @Test
    public void createFindBucketsFrom_withRecordCountAboveLimit_returnsTwoFindBuckets() throws Exception {
        List<FindBucket> findBuckets =
                sensorRecordRepository.createFindBucketsFrom(1001);

        assertThat(findBuckets.size(), equalTo(2));

        assertThat(findBuckets.get(0).getOffset(), equalTo(0L));
        assertThat(findBuckets.get(0).getLimit(), equalTo(1000L));

        assertThat(findBuckets.get(1).getOffset(), equalTo(1000L));
        assertThat(findBuckets.get(1).getLimit(), equalTo(1L));
    }

    @Test
    public void createFindBucketsFrom_withRecordCountVeryAboveLimit_returnsMultipleFindBuckets() throws Exception {
        List<FindBucket> findBuckets =
                sensorRecordRepository.createFindBucketsFrom(12123);

        assertThat(findBuckets.size(), equalTo(13));

        assertThat(findBuckets.get(2).getOffset(), equalTo(2000L));
        assertThat(findBuckets.get(2).getLimit(), equalTo(1000L));

        assertThat(findBuckets.get(12).getOffset(), equalTo(12000L));
        assertThat(findBuckets.get(12).getLimit(), equalTo(123L));
    }

    protected Map<Long, T> provideSensorRecordsToCreate() {
        HashMap<Long, T> recordsMap = new HashMap<>();

        recordsMap.put(0L, createSensorRecord());
        recordsMap.put(1L, createSensorRecord());
        recordsMap.put(2L, createSensorRecord());
        recordsMap.put(3L, createSensorRecord());

        return recordsMap;
    }

    protected List<T> createSensorRecords(int count) {
        List<T> sensorRecords = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            sensorRecords.add(createSensorRecord());
        }
        return sensorRecords;
    }

    protected List<E> createSensorRecordEntities(int count) {
        List<E> sensorEntityRecords = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            sensorEntityRecords.add(createSensorRecordEntity());
        }
        return sensorEntityRecords;
    }

    protected abstract T createSensorRecord();

    protected abstract E createSensorRecordEntity();
}
