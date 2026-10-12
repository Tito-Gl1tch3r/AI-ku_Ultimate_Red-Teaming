package org.jdbg.core;

import java.awt.*;
import java.util.ArrayList;
import java.util.List;

public class Util {

    public static class ProcessData {
        public String processName;
        public long processID;

    }

    public static List<ProcessData> getRunningProcesses() {
        List<ProcessData> list = new ArrayList<>();
        ProcessHandle.allProcesses().forEach(process -> {
            ProcessData data = new ProcessData();
            data.processID = process.pid();
            data.processName = process.info().command().orElse("?");

            data.processName = data.processName.substring(data.processName.lastIndexOf('\\')+1);

            list.add(data);
        });

        return list;
    }

    public static String convertColorToHex(Color color) {
        int red = color.getRed();
        int green = color.getGreen();
        int blue = color.getBlue();

        String hexRed = String.format("%02X", red);
        String hexGreen = String.format("%02X", green);
        String hexBlue = String.format("%02X", blue);

        return "#" + hexRed + hexGreen + hexBlue;
    }
    public static Integer toInteger(byte b1, byte b2, byte b3, byte b4) {

        int test = ((b1 & 0xFF) | ((b2 & 0xFF) << 8) | ((b3 & 0xFF) << 16) | ((b4 & 0xFF) << 24));
        return test;
    }

}
