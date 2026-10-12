package org.jdbg;

import com.formdev.flatlaf.FlatDarkLaf;
import org.fife.ui.rsyntaxtextarea.AbstractTokenMakerFactory;
import org.fife.ui.rsyntaxtextarea.TokenMakerFactory;
import org.jdbg.core.pipeline.impl.PipelineBreakpoint;
import org.jdbg.core.pipeline.impl.PipelineLogDll;
import org.jdbg.gui.MainFrame;
import org.jdbg.core.pipeline.impl.PipelineMain;
import org.jdbg.gui.tabs.classanalysis.codepanel.token.JavaBytecodeTokenMaker;

import javax.swing.*;
import java.awt.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class Main {
    // TODO need to make a process termination callback
    public static void main(String[] args) {
        WrapperMain.wrap();

        AbstractTokenMakerFactory atmf = (AbstractTokenMakerFactory) TokenMakerFactory.getDefaultInstance();
        atmf.putMapping("java-bytecode", JavaBytecodeTokenMaker.class.getName());

        try {
            UIManager.setLookAndFeel(new FlatDarkLaf());

            List<String> colors = new ArrayList<String>();
            for (Map.Entry<Object, Object> entry : UIManager.getDefaults().entrySet()) {
                if (entry.getValue() instanceof Font) {
                    System.out.println(entry.getKey() + " - ");
                }
            }


        } catch (UnsupportedLookAndFeelException e) {
            e.printStackTrace();
        }

        SwingUtilities.invokeLater(new Runnable() {
            @Override
            public void run() {
                final MainFrame wnd = new MainFrame();
                wnd.setVisible(true);

                PipelineMain.init();
                PipelineLogDll.init();
                PipelineBreakpoint.init();

                Thread shutdown = new Thread(() -> {
                    PipelineMain.getInstance().shutdown();
                    PipelineLogDll.getInstance().shutdown();
                    PipelineBreakpoint.getInstance().shutdown();
                });
                Runtime.getRuntime().addShutdownHook(shutdown);
            }
        });




    }

}