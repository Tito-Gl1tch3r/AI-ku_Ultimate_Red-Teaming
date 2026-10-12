package cn.wanghw.spider;

import cn.wanghw.IHeapHolder;
import cn.wanghw.ISpider;
import cn.wanghw.utils.ResultBuffer;

import java.util.Iterator;

public class CookieThief implements ISpider {
    public String getName() {
        return "CookieThief";
    }

    public String sniff(IHeapHolder heapHolder) {
        ResultBuffer result = new ResultBuffer();
        try {
            Object clazz = heapHolder.findClass("java.lang.String");
            if (clazz == null)
                return null;
            Iterator it = heapHolder.getInstancesIterator(clazz);
            while (it.hasNext() && result.hasRoom()) {
                String text = heapHolder.toString(it.next());
                if (text != null && text.indexOf("Cookie:") >= 0) {
                    result.append(text);
                    result.append("\r\n");
                }
            }
        } catch (Exception ex) {
            System.out.println(ex);
        }
        return result.toString();
    }
}
