package org.graalvm.visualvm.lib.jfluid.heap;

import cn.wanghw.IHeapHolder;
import cn.wanghw.utils.HeapHolderSupport;
import cn.wanghw.utils.SpiderLimits;
import cn.wanghw.utils._StringJoiner;
import org.graalvm.visualvm.lib.profiler.oql.engine.api.impl.Snapshot;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

public class GraalvmHeapHolder implements IHeapHolder {
    final private AtomicBoolean cancelled = new AtomicBoolean(false);
    private Heap _heap;
    private Snapshot snapshot;

    public GraalvmHeapHolder(File heapfile) throws IOException {
        _heap = HeapFactory.createHeap(heapfile);
        snapshot = new Snapshot(_heap, this);
    }

    public boolean isCancelled() {
        return cancelled.get();
    }

    public void cancelQuery() {
        cancelled.set(true);
    }

    public JavaClass findClass(String var1) {
        return snapshot.findClass(var1);
    }

    public boolean isArray(Object javaClass) {
        if (javaClass instanceof JavaClass) {
            return ((JavaClass) javaClass).isArray();
        }
        return false;
    }

    public boolean isInstanceOf(Object javaClass, String className) {
        if (javaClass instanceof JavaClass) {
            JavaClass cls = (JavaClass) javaClass;
            for (; cls != null; cls = cls.getSuperClass())
                if (cls.getName().equals(className)) return true;
        }
        return false;
    }

    public JavaClass[] getSubClasses(Object javaClass) {
        if (javaClass instanceof JavaClass) {
            return ((JavaClass) javaClass).getSubClasses().toArray(new JavaClass[0]);
        }
        return new JavaClass[0];
    }

    public Iterator getClasses() {
        return snapshot.getClasses();
    }

    public List getInstances(Object javaClass) {
        if (javaClass instanceof JavaClass) {
            return ((JavaClass) javaClass).getInstances();
        }
        return new ArrayList();
    }

    public Iterator getInstancesIterator(Object javaClass) {
        return HeapHolderSupport.instancesIterator(javaClass);
    }

    public List getFields(Object javaClass) {
        if (javaClass instanceof JavaClass) {
            return ((JavaClass) javaClass).getFields();
        }
        return new ArrayList();
    }

    public String getClassName(Object javaClass) {
        if (javaClass instanceof JavaClass) {
            return ((JavaClass) javaClass).getName();
        }
        return null;
    }

    public Object getSuperClass(Object javaClass) {
        if (javaClass instanceof JavaClass) {
            return ((JavaClass) javaClass).getSuperClass();
        }
        return null;
    }

    public String getFieldName(Object field) {
        if (field instanceof Field) {
            return ((Field) field).getName();
        }
        return null;
    }

    public Object getFieldClass(Object field) {
        if (field instanceof Field) {
            return ((Field) field).getDeclaringClass();
        }
        return null;
    }

    public Object getValueOfField(Object instance, String fieldName) {
        if (instance instanceof Instance) {
            return ((Instance) instance).getValueOfField(fieldName);
        }
        return null;
    }

    public Object findThing(Long objectId) {
        return snapshot.findThing(objectId);
    }

    public HashMap<String, String> getFieldsByNameList(Object instance, HashMap<String, String> fieldList) {
        HashMap<String, String> result = new HashMap<String, String>();
        if (instance == null || fieldList == null) {
            return result;
        }
        for (Map.Entry<String, String> fieldName : fieldList.entrySet()) {
            result.put(fieldName.getKey(), getFieldStringValue(instance, fieldName.getValue()));
        }
        return result;
    }

    public HashMap<String, String> arrayDump(Object instance) {
        HashMap<String, String> result = new HashMap<String, String>();
        if (instance instanceof ObjectArrayDump) {
            ObjectArrayDump arrayDump = (ObjectArrayDump) instance;
            for (Instance _entry : arrayDump.getValues()) {
                if (_entry == null) continue;
                result.put(getFieldStringValue(_entry, "key"), getFieldStringValue(_entry, "value"));
            }
        }
        return result;
    }

    public Instance[] getArrayItems(Object instance) {
        if (instance instanceof ObjectArrayDump) {
            ObjectArrayDump arrayDump = (ObjectArrayDump) instance;
            return arrayDump.getValues().toArray(new Instance[0]);
        }
        return new Instance[0];
    }

    public String getFieldStringValue(Object instance, String fieldName) {
        Object val = getFieldValue(instance, fieldName);
        if (val instanceof Instance) {
            return toString((Instance) val);
        } else if (val != null) {
            return String.valueOf(val);
        }
        return null;
    }

    public Object getFieldValue(Object _instance, String fieldName) {
        if (_instance == null || fieldName == null || !(_instance instanceof Instance)) {
            return null;
        }
        Instance instance = (Instance) _instance;
        if (fieldName.contains(".")) {
            Object fInstance = instance.getValueOfField(fieldName.substring(0, fieldName.indexOf(".")));
            if (fInstance != null) {
                return getFieldValue((Instance) fInstance, fieldName.substring(fieldName.indexOf(".") + 1));
            } else {
                return null;
            }
        } else {
            if (fieldName.equals("@ID"))
                return String.valueOf(instance.getInstanceId());
            Object fInstance = instance.getValueOfField(fieldName);
            if (fInstance != null) {
                if (fInstance instanceof Integer) {
                    return String.valueOf(fInstance);
                }
                return instance.getValueOfField(fieldName);
            } else {
                return null;
            }
        }
    }

    static final List<String> mapClassList = Arrays.asList(
            "java.util.HashMap",
            "java.util.Properties",
            "java.util.LinkedHashMap",
            "java.util.Collections$UnmodifiableMap"
    );

    public boolean isMap(Object _instance) {
        if (_instance != null) {
            Instance instance = (Instance) _instance;
            String className = instance.getJavaClass().getName();
            return mapClassList.contains(className);
        } else return false;
    }

    public Instance getMap(Object _instance) {
        if (_instance != null) {
            Instance instance = (Instance) _instance;
            Object table = instance.getValueOfField("table");
            if (table == null)
                table = getFieldValue(instance, "source.table");
            if (table != null) {
                return (Instance) table;
            } else {
                Object m1 = instance.getValueOfField("m");
                if (m1 != null) {
                    Object m2 = ((Instance) m1).getValueOfField("m");
                    if (m2 != null) {
                        return (Instance) ((Instance) m2).getValueOfField("table");
                    } else {
                        return (Instance) ((Instance) m1).getValueOfField("table");
                    }
                } else {
                    return null;
                }
            }
        } else return null;
    }

    public String toString(Object _instance) {
        return toStringRecursive(_instance, new HashSet(), 0);
    }

    private String toStringRecursive(Object _instance, HashSet visited, int depth) {
        if (_instance == null || !(_instance instanceof Instance)) {
            return null;
        }
        if (depth > SpiderLimits.MAX_TOSTRING_DEPTH) {
            return "";
        }
        Instance instance = (Instance) _instance;
        Long id = Long.valueOf(instance.getInstanceId());
        if (!visited.add(id)) {
            return "";
        }
        String instanceClassName = instance.getJavaClass().getName();
        if ("java.lang.String".equals(instanceClassName)) {
            return decodeString(instance);
        }
        if ("char[]".equals(instanceClassName)) {
            return decodeCharArray(instance);
        }
        Object val = instance.getValueOfField("value");
        if (val instanceof Instance) {
            return toStringRecursive(val, visited, depth + 1);
        }
        return null;
    }

    private String decodeString(Instance instance) {
        Object value = instance.getValueOfField("value");
        Object coder = instance.getValueOfField("coder");
        Object offset = instance.getValueOfField("offset");
        Object count = instance.getValueOfField("count");
        int charLen = HeapHolderSupport.estimateCharLength(value, coder, offset, count);
        int maxChars = SpiderLimits.maxStringChars();
        if (charLen >= 0 && charLen <= maxChars) {
            String s = snapshot.valueString(instance);
            return s != null ? s : "";
        }
        String sliced = HeapHolderSupport.decodeArraySlice(value, coder, offset, maxChars);
        return sliced == null ? "" : sliced + "...";
    }

    private String decodeCharArray(Instance instance) {
        int len = HeapHolderSupport.arrayLength(instance);
        int maxChars = SpiderLimits.maxStringChars();
        if (len >= 0 && len <= maxChars) {
            String s = snapshot.valueString(instance);
            if (s != null) {
                return s;
            }
        }
        int take = len < 0 ? maxChars : Math.min(len, maxChars);
        String sliced = HeapHolderSupport.decodeArraySlice(instance, null, null, take);
        if (sliced == null) {
            return "";
        }
        return len > maxChars ? sliced + "..." : sliced;
    }

    public byte[] toByteArray(Object _instance) {
        if (!(_instance instanceof PrimitiveArrayInstance)) {
            return null;
        }
        PrimitiveArrayInstance array = (PrimitiveArrayInstance) _instance;
        if (!"byte[]".equals(array.getJavaClass().getName())) {
            return null;
        }
        int len = array.getLength();
        if (len < 0) {
            return null;
        }
        if (len > SpiderLimits.maxByteArray()) {
            len = SpiderLimits.maxByteArray();
        }
        return HeapHolderSupport.getBytes(array, 0, len);
    }

    public void dispose() {
        HeapHolderSupport.closeQuietly(_heap);
        HeapHolderSupport.closeQuietly(snapshot);
        _heap = null;
        snapshot = null;
    }

    public String join(CharSequence delimiter,
                       Iterable<? extends CharSequence> elements) {
        _StringJoiner.requireNonNull(delimiter);
        _StringJoiner.requireNonNull(elements);
        _StringJoiner joiner = new _StringJoiner(delimiter);
        for (CharSequence cs : elements) {
            joiner.add(cs);
        }
        return joiner.toString();
    }
}
