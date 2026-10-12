package cn.wanghw.spider;

import cn.wanghw.IHeapHolder;
import cn.wanghw.ISpider;
import cn.wanghw.utils.HashMapUtils;
import cn.wanghw.utils.SpiderLimits;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;

public class OSS01 implements ISpider {
    public String getName() {
        return "OSS";
    }

    final List<String> ossKeywords = Collections.unmodifiableList(Arrays.asList("key", "id", "secret", "access", "bucket", "endpoint", "sk"));

    private boolean judge(String key) {
        key = key.toLowerCase();
        if (key.indexOf("oss.") >= 0 || key.indexOf("s3.") >= 0 || key.indexOf("cos.") >= 0 || key.indexOf("lbs.") >= 0 || key.indexOf("storage.") >= 0 || (key.indexOf("file") >= 0 && key.indexOf("upload") >= 0)) {
            for (int i = 0; i < ossKeywords.size(); i++) {
                if (key.indexOf(ossKeywords.get(i)) >= 0) {
                    return true;
                }
            }
        }
        return false;
    }

    public String sniff(IHeapHolder heapHolder) {
        final StringBuilder result = new StringBuilder();
        try {
            LinkedHashMap<String, String> values = new LinkedHashMap<String, String>();
            List<Object> mapEntryClasses = new ArrayList<Object>();
            HashSet<String> seenClasses = new HashSet<String>();
            for (Iterator it = heapHolder.getClasses(); it.hasNext(); ) {
                Object clazz = it.next();
                String clazzName = heapHolder.getClassName(clazz);
                if (clazzName == null) {
                    continue;
                }
                clazzName = clazzName.toLowerCase();
                int dollar = clazzName.lastIndexOf('$');
                if (dollar < 0 || dollar + 1 >= clazzName.length()) {
                    continue;
                }
                String inner = clazzName.substring(dollar + 1);
                if ((inner.endsWith("entry") || inner.endsWith("node")) && seenClasses.add(clazzName)) {
                    mapEntryClasses.add(clazz);
                }
            }
            for (int i = 0; i < mapEntryClasses.size(); i++) {
                dump(heapHolder, values, mapEntryClasses.get(i));
            }
            result.append(HashMapUtils.dumpString(values, false));
        } catch (Exception ex) {
            System.out.println(ex);
        }
        return result.toString();
    }

    private void dump(IHeapHolder heapHolder, LinkedHashMap<String, String> values, Object clazz) {
        Iterator it = heapHolder.getInstancesIterator(clazz);
        int visited = 0;
        while (it.hasNext() && SpiderLimits.allowMoreInstances(visited)) {
            Object instance = it.next();
            visited++;
            String key = heapHolder.getFieldStringValue(instance, "key");
            if (key != null && judge(key)) {
                String val = heapHolder.getFieldStringValue(instance, "value");
                if (val != null && !val.equals("")) {
                    values.put(key, val);
                }
            }
        }
    }
}
