package cn.wanghw.spider;

import cn.wanghw.IHeapHolder;
import cn.wanghw.ISpider;
import cn.wanghw.utils.HashMapUtils;
import cn.wanghw.utils.SpiderLimits;

import java.util.HashMap;
import java.util.Iterator;

public class PropertySource05 implements ISpider {

    public String getName() {
        return "JavaProperties";
    }


    public String sniff(IHeapHolder heapHolder) {

        final StringBuilder result = new StringBuilder();
        try {
            Object clazz = heapHolder.findClass("java.util.Properties");
            if (clazz == null)
                return null;
            HashMap<String, String> values = new HashMap<String, String>();
            Iterator it = heapHolder.getInstancesIterator(clazz);
            int visited = 0;
            while (it.hasNext() && SpiderLimits.allowMoreInstances(visited)) {
                values.putAll(heapHolder.arrayDump(heapHolder.getMap(it.next())));
                visited++;
            }
            result.append(HashMapUtils.dumpString(values, false));
        } catch (Exception ex) {
            System.out.println(ex);
        }
        return result.toString();
    }
}
