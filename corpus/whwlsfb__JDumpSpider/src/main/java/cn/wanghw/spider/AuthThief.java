package cn.wanghw.spider;

import cn.wanghw.IHeapHolder;
import cn.wanghw.ISpider;
import cn.wanghw.utils.HashMapUtils;
import cn.wanghw.utils.ResultBuffer;
import cn.wanghw.utils.SpiderLimits;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;

public class AuthThief implements ISpider {
    public String getName() {
        return "AuthThief";
    }

    private boolean judge(String key) {
        key = key.toLowerCase();
        if (key.equals("authorization")) {
            return true;
        } else if (key.indexOf("auth") >= 0) {
            return true;
        } else if (key.indexOf("cookie") >= 0) {
            return true;
        } else if (key.indexOf("token") >= 0) {
            return true;
        }
        return false;
    }

    public String sniff(IHeapHolder heapHolder) {
        ResultBuffer result = new ResultBuffer();
        try {
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
            for (int i = 0; i < mapEntryClasses.size() && result.hasRoom(); i++) {
                Object clazz = mapEntryClasses.get(i);
                LinkedHashMap<String, String> values = new LinkedHashMap<String, String>();
                dump(heapHolder, values, clazz);
                if (!values.isEmpty()) {
                    result.append(heapHolder.getClassName(clazz));
                    result.append(":\r\n");
                    result.append(HashMapUtils.dumpString(values, false));
                    result.append("\r\n");
                }
            }
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
