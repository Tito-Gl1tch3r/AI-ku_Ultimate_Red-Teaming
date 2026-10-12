package cn.wanghw;

import cn.wanghw.spider.*;
import cn.wanghw.utils.SpiderLimits;
import org.graalvm.visualvm.lib.jfluid.heap.GraalvmHeapHolder;
import org.netbeans.lib.profiler.heap.NetbeansHeapHolder;

import java.io.*;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

public class Main {

    private File heapfile;
    private final List<String> flag = new LinkedList<String>();
    static PrintStream out = null;

    public static String run(String[] args) throws Exception {
        ByteArrayOutputStream bout = new ByteArrayOutputStream();
        PrintStream runOut = out;
        boolean closeRunOut = false;
        if (runOut == null) {
            runOut = new PrintStream(bout);
            closeRunOut = true;
        }
        try {
            if (args.length < 1) {
                runOut.println("please give a heap filepath.");
            } else {
                Main _main = new Main();
                _main.heapfile = new File(args[0]);
                if (_main.heapfile.exists() && _main.heapfile.isFile()) {
                    if (args.length > 1) {
                        _main.flag.addAll(Arrays.asList(args).subList(1, args.length));
                    }
                    _main.call(runOut);
                } else {
                    runOut.println("file not exist!");
                }
            }
        } finally {
            if (closeRunOut) {
                runOut.close();
            }
        }
        return bout.toString();
    }

    public static String runAsync(final String[] args) throws Exception {
        if (args.length < 2)
            return "In async call, you must give a result file path";
        Thread thread = new Thread(new Runnable() {
            public void run() {
                FileOutputStream fos = null;
                try {
                    String result = Main.run(args);
                    fos = new FileOutputStream(args[1]);
                    fos.write(result.getBytes());
                } catch (Throwable e) {
                    throw new RuntimeException(e);
                } finally {
                    if (fos != null) {
                        try {
                            fos.close();
                        } catch (IOException ignored) {
                        }
                    }
                }
            }
        });
        thread.setDaemon(true);
        thread.start();
        return "start export thread:" + thread.getName();
    }

    public static void main(String[] args) throws Exception {
        out = System.out;
        run(args);
    }

    private ISpider[] allSpiders = new ISpider[]{
            new DataSource01(),
            new DataSource02(),
            new DataSource03(),
            new DataSource04(),
            new DataSource05(),
            new Redis01(),
            new Redis02(),
            new ShiroKey01(),
            new PropertySource01(),
            new PropertySource02(),
            new PropertySource03(),
            new PropertySource04(),
////            new JwtKey01(),
            new PropertySource05(),
            new EnvProperty01(),
            new OSS01(),
            new UserPassSearcher01(),
            new CookieThief(),
            new AuthThief()
    };

    public int call(PrintStream out) throws Exception {
        int ver = getFileVersion();
        float classVersion = Float.parseFloat(System.getProperty("java.class.version"));
        IHeapHolder heapHolder = null;
        PrintStream fileOut = null;
        PrintStream targetOut = out;

        try {
            try {
                if (ver == 1 || classVersion < 52) {
                    heapHolder = new NetbeansHeapHolder(heapfile);
                } else {
                    heapHolder = new GraalvmHeapHolder(heapfile);
                }
            } catch (Throwable t) {
                targetOut.println("[-] Failed to open heap dump: " + t.getMessage());
                if (t instanceof Error) {
                    throw (Error) t;
                }
                throw new Exception("Failed to open heap dump", t);
            }
            SpiderLimits.refresh();
            System.out.println("[+] SpiderLimits: " + SpiderLimits.describe());
            if (flag.contains("export-strings")) {
                if (!spiderCall(new ExportAllString(), heapHolder, targetOut)) {
                    return 1;
                }
                return 0;
            }
            if (flag.contains("-out")) {
                String outFilePath = getArgValue("-out");
                System.out.println("[+] Output to: " + outFilePath);
                fileOut = new PrintStream(new FileOutputStream(outFilePath), true);
                targetOut = fileOut;
            }
            for (int i = 0; i < allSpiders.length; i++) {
                if (!spiderCall(allSpiders[i], heapHolder, targetOut)) {
                    targetOut.println("[-] abort remaining spiders after fatal error.");
                    break;
                }
            }
            targetOut.println("===========================================");
            return 0;
        } finally {
            if (heapHolder != null) {
                heapHolder.dispose();
            }
            if (fileOut != null) {
                fileOut.close();
            } else if (targetOut != null) {
                targetOut.flush();
            }
            System.gc();
        }
    }

    private String getArgValue(String flagStr) throws Exception {
        try {
            return flag.get(flag.indexOf(flagStr) + 1);
        } catch (IndexOutOfBoundsException e) {
            throw new Exception("[-] Get '" + flagStr + "' value failed!");
        }
    }

    private boolean spiderCall(ISpider spider, IHeapHolder heapHolder, PrintStream out) {
        out.println("===========================================");
        out.println(spider.getName());
        out.println("-------------");
        try {
            String result = spider.sniff(heapHolder);
            if (result != null && result.length() > 0) {
                out.println(result);
            } else {
                out.println("not found!\r\n");
            }
            return true;
        } catch (StackOverflowError e) {
            out.println("[-] aborted: stack overflow (cyclic object graph)\r\n");
            return true;
        } catch (OutOfMemoryError e) {
            System.gc();
            SpiderLimits.refresh();
            out.println("[-] aborted: out of memory\r\n");
            return false;
        } finally {
            recoverHeapBudget();
        }
    }

    private void recoverHeapBudget() {
        SpiderLimits.refresh();
        if (SpiderLimits.lowMemory()) {
            System.gc();
            SpiderLimits.refresh();
        }
    }

    public int getFileVersion() {
        FileInputStream io = null;
        try {
            io = new FileInputStream(heapfile);
            byte[] header = new byte[18];
            int n = 0;
            while (n < header.length) {
                int r = io.read(header, n, header.length - n);
                if (r < 0) {
                    break;
                }
                n += r;
            }
            if (n < 18) {
                throw new IOException("file too small to be a heap dump");
            }
            String magic = new String(header, 0, 12, "US-ASCII");
            if (!"JAVA PROFILE".equals(magic)) {
                throw new IOException("not a HPROF heap dump (missing JAVA PROFILE header)");
            }
            char versionChar = (char) (header[17] & 0xff);
            if (versionChar < '0' || versionChar > '9') {
                throw new IOException("invalid HPROF version byte");
            }
            return versionChar - '0';
        } catch (Exception e) {
            throw new RuntimeException(e);
        } finally {
            if (io != null) {
                try {
                    io.close();
                } catch (IOException ignored) {
                }
            }
        }
    }
}
