package org.jdbg.gui.tabs.objectanalysis;

import org.jdbg.core.CoreInterface;
import org.jdbg.core.pipeline.response.FieldResponseData;
import org.jdbg.core.pipeline.response.SubGraphData;
import org.jdbg.gui.tabs.objectanalysis.objinfo.ObjectInfo;
import org.jdbg.gui.tabs.objectanalysis.objlist.ObjectListPanel;
import org.jdbg.gui.tabs.objectanalysis.objlist.TagItem;

import javax.swing.*;
import java.awt.*;
import java.util.Map;

public class MainHeapPanel extends JPanel {

    ObjectListPanel list;
    JPanel objectInfo;
    JScrollPane objectInfoScrollPane;

    public MainHeapPanel(ObjectAnalysisClassTree tree) {
        setLayout(new GridBagLayout());

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.VERTICAL;
        gbc.weighty = 1;
        gbc.anchor = GridBagConstraints.NORTHWEST;

        list = new ObjectListPanel(tree);
        add(list, gbc);


        GridBagConstraints g = new GridBagConstraints();
        g.fill = GridBagConstraints.BOTH;
        g.gridwidth = GridBagConstraints.REMAINDER;
        g.gridheight = GridBagConstraints.REMAINDER;


        g.weightx = 1;
        g.weighty = 1;
        g.anchor = GridBagConstraints.SOUTHWEST;

        objectInfo = new JPanel();
        objectInfoScrollPane = new JScrollPane(objectInfo, JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED, JScrollPane.HORIZONTAL_SCROLLBAR_ALWAYS);
        add(objectInfoScrollPane, g);

    }

    public void initObjectInfo(TagItem tagItem) {
        Map<Integer, SubGraphData> refs = CoreInterface.getInstance().getReferences(tagItem);
        if(refs==null) {
            return;
        }

        FieldResponseData fields = CoreInterface.getInstance().getFields(tagItem);
        if(fields==null) {
            fields = new FieldResponseData();
            //return;
        }
        objectInfo = new ObjectInfo(tagItem,  fields, refs);
        objectInfoScrollPane.setViewportView(objectInfo);
    }

    public ObjectListPanel getObjectList() {
        return list;
    }
}
