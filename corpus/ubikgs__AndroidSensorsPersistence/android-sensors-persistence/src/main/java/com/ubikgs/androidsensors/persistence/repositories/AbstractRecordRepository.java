package com.ubikgs.androidsensors.persistence.repositories;

import com.ubikgs.androidsensors.persistence.daos.RecordEntityDao;
import com.ubikgs.androidsensors.persistence.entities.RecordEntity;
import com.ubikgs.androidsensors.persistence.repositories.common.FindBucket;
import com.ubikgs.androidsensors.records.SensorRecord;

import java.util.Collection;
import java.util.LinkedList;
import java.util.List;

import io.reactivex.BackpressureStrategy;
import io.reactivex.Flowable;
import io.reactivex.Observable;
import io.reactivex.Single;
import io.reactivex.functions.Function;

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

public abstract class AbstractRecordRepository<T extends SensorRecord, E extends RecordEntity<T>>
        implements RecordRepository<T> {

    private static final int RESULT_COUNT_LIMIT = 1000;

    private final RecordEntityDao<E> recordEntityDao;

    public AbstractRecordRepository(RecordEntityDao<E> recordEntityDao) {
        this.recordEntityDao = recordEntityDao;
    }

    public Single<List<Long>> createAll(Collection<T> sensorRecords) {
        return Observable.fromIterable(sensorRecords)
                .map(new Function<T, E>() {
                    @Override
                    public E apply(T sensorRecord) throws Exception {
                        return createFrom(sensorRecord);
                    }
                })
                .toList()
                .map(new Function<List<E>, List<Long>>() {
                    @Override
                    public List<Long> apply(List<E> sensorRecordEntities) throws Exception {
                        return recordEntityDao.createAll(sensorRecordEntities);
                    }
                });
    }

    public Single<List<Long>> createAll(Collection<T> sensorRecords, final Long foreignKey) {
        return Observable.fromIterable(sensorRecords)
                .map(new Function<T, E>() {
                    @Override
                    public E apply(T sensorRecord) throws Exception {
                        return createFrom(sensorRecord);
                    }
                })
                .map(new Function<E, E>() {
                    @Override
                    public E apply(E sensorRecordEntity) throws Exception {
                        sensorRecordEntity.setForeignKey(foreignKey);
                        return sensorRecordEntity;
                    }
                })
                .toList()
                .map(new Function<List<E>, List<Long>>() {
                    @Override
                    public List<Long> apply(List<E> sensorRecordEntities) throws Exception {
                        return recordEntityDao.createAll(sensorRecordEntities);
                    }
                });
    }

    protected abstract E createFrom(T sensorRecord);

    public Flowable<T> findAll() {
        return findAllWith(
                new Counter() {
                    @Override
                    public Single<Long> count() {
                        return recordEntityDao.count();
                    }
                },
                new Finder<E>() {
                    @Override
                    public Single<List<E>> find(FindBucket findBucket) {
                        return recordEntityDao.findAll(
                                findBucket.getOffset(), findBucket.getLimit());
                    }
                }
        );
    }

    public Single<Long> count() {
        return recordEntityDao.count();
    }

    public void removeAll() {
        recordEntityDao.removeAll();
    }

    public Flowable<T> findAllBy(final long foreignKey) {
        return findAllWith(
                new Counter() {
                    @Override
                    public Single<Long> count() {
                        return recordEntityDao.countBy(foreignKey);
                    }
                },
                new Finder<E>() {
                    @Override
                    public Single<List<E>> find(FindBucket findBucket) {
                        return recordEntityDao.findAllBy(
                                foreignKey, findBucket.getOffset(), findBucket.getLimit());
                    }
                }
        );
    }

    public Single<Long> countBy(long foreignKey) {
        return recordEntityDao.countBy(foreignKey);
    }

    public void removeAllBy(long foreignKey) {
        recordEntityDao.removeAllBy(foreignKey);
    }

    private Flowable<T> findAllWith(Counter counter, final Finder<E> finder) {
        return counter.count()
                .map(new Function<Long, List<FindBucket>>() {
                    @Override
                    public List<FindBucket> apply(Long count) throws Exception {
                        return createFindBucketsFrom(count);
                    }
                })
                .flatMapObservable(new Function<List<FindBucket>, Observable<FindBucket>>() {
                    @Override
                    public Observable<FindBucket> apply(List<FindBucket> findBuckets) throws Exception {
                        return Observable.fromIterable(findBuckets);
                    }
                })
                .flatMapSingle(new Function<FindBucket, Single<List<E>>>() {
                    @Override
                    public Single<List<E>> apply(FindBucket findBucket) throws Exception {
                        return finder.find(findBucket);
                    }
                })
                .map(new Function<List<E>, Observable<E>>() {
                    @Override
                    public Observable<E> apply(List<E> entities) throws Exception {
                        return Observable.fromIterable(entities);
                    }
                })
                .flatMap(new Function<Observable<E>, Observable<T>>() {
                    @Override
                    public Observable<T> apply(Observable<E> recordEntityObservable) throws Exception {
                        return recordEntityObservable.map(new Function<E, T>() {
                            @Override
                            public T apply(E entity) throws Exception {
                                return transformIn(entity);
                            }
                        });
                    }
                })
                .toFlowable(BackpressureStrategy.BUFFER);
    }

    protected abstract T transformIn(E entity);

    private interface Counter {
        Single<Long> count();
    }

    private interface Finder<E extends RecordEntity> {
        Single<List<E>> find(FindBucket findBucket);
    }

    protected List<FindBucket> createFindBucketsFrom(long count) {
        return Observable.fromIterable(createFindBucketsFrom(count, count))
                .sorted()
                .toList()
                .blockingGet();
    }

    private List<FindBucket> createFindBucketsFrom(long count, long remaining) {
        if (remaining < RESULT_COUNT_LIMIT) {
            LinkedList<FindBucket> findBuckets = new LinkedList<>();
            findBuckets.add(new FindBucket(count - remaining, remaining));
            return findBuckets;
        }

        List<FindBucket> findBuckets = createFindBucketsFrom(count, remaining - RESULT_COUNT_LIMIT);
        findBuckets.add(new FindBucket(count - remaining, RESULT_COUNT_LIMIT));
        return findBuckets;
    }

}
