package cn.wanghw.spider;

import cn.wanghw.IHeapHolder;
import cn.wanghw.ISpider;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.util.Iterator;

public class ExportAllString implements ISpider {

    public String getName() {
        return "ExportAllString";
    }

    public String sniff(IHeapHolder heapHolder) {
        BufferedWriter writer = null;
        try {
            File outFile = new File(System.nanoTime() + ".txt");
            writer = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(outFile)));
            System.out.println("[+] Output to: " + outFile.getAbsolutePath());
            Object clazz = heapHolder.findClass("java.lang.String");
            if (clazz == null)
                return null;
            Iterator it = heapHolder.getInstancesIterator(clazz);
            int written = 0;
            while (it.hasNext()) {
                String text = heapHolder.toString(it.next());
                if (text != null) {
                    writer.write(text);
                    writer.newLine();
                    written++;
                    if ((written & 0x3FFF) == 0) {
                        writer.flush();
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println(ex);
        } finally {
            if (writer != null) {
                try {
                    writer.close();
                } catch (IOException ignored) {
                }
            }
        }
        return "\r\n";
    }
}
