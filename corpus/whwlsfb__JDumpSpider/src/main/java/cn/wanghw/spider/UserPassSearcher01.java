package cn.wanghw.spider;

import cn.wanghw.IHeapHolder;
import cn.wanghw.ISpider;
import cn.wanghw.utils.HashMapUtils;
import cn.wanghw.utils.HeapHolderSupport;
import cn.wanghw.utils.ResultBuffer;
import cn.wanghw.utils.SpiderLimits;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;

public class UserPassSearcher01 implements ISpider {
    public String getName() {
        return "UserPassSearcher";
    }

    static final List<String> keywordList = Collections.unmodifiableList(Arrays.asList(
            "username",
            "pass"
    ));

    static final List<String> unimportantKeywordList = Collections.unmodifiableList(Arrays.asList(
            "host",
            "user",
            "access",
            "key",
            "jdbc",
            "url",
            "uri",
            "token",
            "database",
            "db",
            "secret",
            "phone",
            "email",
            "enterprise",
            "login",
            "server",
            "addr",
            "iv",
            "salt"
    ));

    public String sniff(IHeapHolder heapHolder) {
        ResultBuffer result = new ResultBuffer();
        try {
            for (Iterator it = heapHolder.getClasses(); it.hasNext() && result.hasRoom(); ) {
                Object clazz = it.next();
                String className = heapHolder.getClassName(clazz);
                if (className == null || heapHolder.isArray(clazz) || className.indexOf('[') >= 0) {
                    continue;
                }
                List<String> fieldList = new LinkedList<String>();
                fieldList.addAll(HeapHolderSupport.findFieldsByKeywords(heapHolder, clazz, keywordList));
                if (fieldList.isEmpty()) continue;
                fieldList.addAll(HeapHolderSupport.findFieldsByKeywords(heapHolder, clazz, unimportantKeywordList));
                HashMap<String, String> fieldMap = new HashMap<String, String>();
                for (int i = 0; i < fieldList.size(); i++) {
                    String fieldName = fieldList.get(i);
                    fieldMap.put(fieldName, fieldName);
                }
                StringBuilder subResult = new StringBuilder();
                boolean isAllEmpty = true;
                subResult.append(className).append(":\r\n");
                List<String> instanceInfo = new LinkedList<String>();
                Iterator instances = heapHolder.getInstancesIterator(clazz);
                int visited = 0;
                while (instances.hasNext() && SpiderLimits.allowMoreInstances(visited) && result.hasRoom()) {
                    Object instance = instances.next();
                    visited++;
                    String dumpString = HashMapUtils.dumpString(heapHolder.getFieldsByNameList(instance, fieldMap), true, false, true);
                    if (!dumpString.equals("")) {
                        isAllEmpty = false;
                        instanceInfo.add("[" + dumpString + "]");
                    }
                }
                if (!isAllEmpty) {
                    Object[] instanceArray = (new HashSet<String>(instanceInfo)).toArray();
                    result.append(subResult.toString());
                    for (int i = 0; i < instanceArray.length && result.hasRoom(); i++) {
                        result.append(String.valueOf(instanceArray[i]));
                        result.append("\r\n");
                    }
                    result.append("\r\n");
                }
            }
        } catch (Exception ex) {
            System.out.println(ex);
        }
        return result.toString();
    }
}
