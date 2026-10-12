package com.codehack.JungleConfig.DataModel;

import com.codehack.JungleConfig.Utils.JLogger;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public class TypeMap<T, D, S> {
    private List<Entry<T, D, S>> dataList = new ArrayList<>();

    public Entry<T, D, S> getEntry(T key) {
        if (!containsKey(key))
            return null;
        return dataList.get(indexOf(key));
    }

    public List<Entry<T, D, S>> getEntryList() {
        return dataList;
    }

    public List<T> getKeyList() {
        List<T> dat = new ArrayList<>();
        for (Entry<T, D, S> data : dataList) {
            dat.add(data.getKey());
        }
        return dat;
    }

    public void clear() {
        dataList.clear();
    }

    public boolean remove(String key) {
        boolean x = dataList.remove(new Entry<>(key, null, null));
        return x;
    }

    public Integer indexOf(T key) {
        return dataList.indexOf(new Entry<>(key, null, null));
    }

    public boolean containsKey(T key) {
        return dataList.contains(new Entry<>(key, null, null));
    }

    public void put(T key, D v1, S v2) {
        if (containsKey(key)) {
            dataList.set(indexOf(key), new Entry<>(key, v1, v2));
        } else {
            dataList.add(new Entry<>(key, v1, v2));
        }
    }

    public void put(Entry<T, D, S> entry) {
        if (containsKey(entry.getKey())) {
            dataList.set(indexOf(entry.getKey()), entry);
        } else {
            dataList.add(entry);
        }
    }

    @Override
    public String toString() {
        return "TripleMap{" +
                "dataList=" + dataList +
                '}';
    }

    public Entry<T, D, S> get(T key) {
        return getEntry(key);
    }

    public Entry<T, D, S> getFromIndex(int index) {
        return dataList.get(index);
    }

    public void setFromIndex(int index, T key, D v1, S v2) {
        dataList.set(index, new Entry<>(key, v1, v2));
    }

    public D getValue1(T key) {
        return getEntry(key).getValue1();
    }

    public S getValue2(T key) {
        return getEntry(key).getValue2();
    }

    public List<Entry<T, D, S>> getEntriesOfv1(D v1) {
        List<Entry<T, D, S>> dtaKeys = new ArrayList<>();
        for (Entry<T, D, S> entry : dataList) {
            if (entry.getValue1().equals(v1))
                dtaKeys.add(entry);
        }
        return dtaKeys;
    }

    public List<Entry<T, D, S>> getEntriesOfv2(S v2) {
        List<Entry<T, D, S>> dtaKeys = new ArrayList<>();
        for (Entry<T, D, S> entry : dataList) {
            if (entry.getValue2().equals(v2))
                dtaKeys.add(entry);
        }
        return dtaKeys;
    }

    public static class Entry<T, D, S> {
        private T key;
        private D value1;
        private S value2;

        public Entry() {
        }

        public Entry(T key, D v1, S v2) {
            this.key = key;
            value1 = v1;
            value2 = v2;
        }

        private boolean isKey(T key) {
            if (key != null) {
                return key.equals(this.key);
            }
            return false;
        }

        @Override
        public String toString() {
            return "Entry{" +
                    "key=" + key +
                    ", value1=" + value1 +
                    ", value2=" + value2 +
                    '}';
        }

        @Override
        public boolean equals(Object o) {
            if (this == o)
                return true;
            if (o == null)
                return false;
            if (getClass() != o.getClass()) {
                if (o == null)
                    return false;
                if (key.getClass() != o.getClass())
                    return false;
                return o.equals(key);
            }
            Entry<?, ?, ?> entry = (Entry<?, ?, ?>) o;
            return Objects.equals(key, entry.key);
        }

        @Override
        public int hashCode() {
            return Objects.hash(key);
        }

        public T getKey() {
            return key;
        }

        public void setKey(T key) {
            this.key = key;
        }

        public D getValue1() {
            return value1;
        }

        public void setValue1(D value1) {
            this.value1 = value1;
        }

        public S getValue2() {
            return value2;
        }

        public void setValue2(S value2) {
            this.value2 = value2;
        }
    }

    public static <T, D, S> TypeMap<T, D, S> of() {
        return new TypeMap<>();
    }
}
