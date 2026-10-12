package org.jdbg.gui;

import org.jdbg.MiscUtil;
import org.jdbg.gui.buttonbar.buttons.AttachProcessButton;
import org.jdbg.gui.menubar.TopMenuBar;
import org.jdbg.gui.log.LogPane;
import org.jdbg.logger.Logger;

import javax.swing.*;
import java.awt.*;

public class MainFrame extends JFrame {

    MainTabbedPane mainTabbedPane = new MainTabbedPane();
    private static MainFrame instance;

    JLabel text = new JLabel();

    public MainFrame() {
        super("JDBG");
        instance = this;
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        initUI();
        getContentPane().setLayout(new BoxLayout(getContentPane(), BoxLayout.Y_AXIS));
        setPreferredSize(new Dimension(1000, 700));

        setupMenuBar();
        setupTopButtons();
        setupSplitPane();
        setupBottomBar();
        pack();
        getContentPane().requestFocus(); // remove annoying focus thing
        Logger.log("JDBG initialisation complete");


    }

    void initUI() {
        try {
            Icon folderIcon = MiscUtil.getIcon("assets/icons/ic_fluent_folder_24_filled.png", 15, 15);
            Icon coffeeIcon = MiscUtil.getIcon("assets/icons/ic_fluent_drink_coffee_24_filled.png", 15, 15);
            UIManager.put("Tree.closedIcon", folderIcon);
            UIManager.put("Tree.openIcon", folderIcon);

            UIManager.put("Tree.leafIcon", coffeeIcon);
        } catch (NullPointerException e) {
            e.printStackTrace();
        }
    }
    void setupMenuBar() {
        setJMenuBar(new TopMenuBar());
    }

    void setupBottomBar() {
        JPanel bottomBar = new JPanel();

        bottomBar.setBackground(UIManager.getColor("TextField.background"));
        bottomBar.setLayout(new FlowLayout(FlowLayout.LEADING));
        bottomBar.setAlignmentX(Component.LEFT_ALIGNMENT);

        bottomBar.add(new JTextArea("JDBG v1.0.0"));

        bottomBar.setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, UIManager.getColor("Button.borderColor")));

        getContentPane().add(bottomBar);

    }

    void setupTopButtons() {
        JPanel topButtons = new JPanel();

        topButtons.add(new AttachProcessButton());
        //topButtons.add(new AttachJarButton());

        text.setText("Not attached");
        text.setForeground(Color.RED);
        topButtons.add(text);

        topButtons.setLayout(new FlowLayout(FlowLayout.LEADING));
        topButtons.setAlignmentX(Component.LEFT_ALIGNMENT);
        getContentPane().add(topButtons);
    }

    void setupSplitPane() {
        JSplitPane splitPane = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT);


        // TODO not sure exactly why but without this it breaks the ui if it goes below the preferred size (bruh)
        splitPane.setPreferredSize(new Dimension(0, 0));
        splitPane.setResizeWeight(0.87);
        splitPane.add(mainTabbedPane);
        splitPane.add((new LogPane()));
        getContentPane().add(splitPane);
    }

    public MainTabbedPane getMainPane() {
        return mainTabbedPane;
    }


    public void setAttached(String process) {
        text.setForeground(Color.GREEN);
        text.setText("Attached: " + process);
    }

    public void setUnattached() {
        text.setText("Not attached");
        text.setForeground(Color.RED);
    }

    public static MainFrame getInstance() {
        return instance;
    }
}
