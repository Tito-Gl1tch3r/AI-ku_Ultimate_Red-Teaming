package org.jdbg.gui.tabs.objectanalysis.objinfo;

import com.mxgraph.layout.hierarchical.mxHierarchicalLayout;
import com.mxgraph.model.mxCell;
import com.mxgraph.model.mxGeometry;
import com.mxgraph.swing.mxGraphComponent;
import com.mxgraph.util.mxConstants;
import com.mxgraph.view.mxStylesheet;
import org.jdbg.core.CoreInterface;
import org.jdbg.core.Util;
import org.jdbg.core.pipeline.response.FieldData;
import org.jdbg.core.pipeline.response.FieldResponseData;
import org.jdbg.core.pipeline.response.SubGraphData;
import org.jdbg.gui.tabs.objectanalysis.objinfo.graph.HeapEdge;
import org.jdbg.gui.tabs.objectanalysis.objinfo.graph.HeapVertex;
import org.jdbg.gui.tabs.objectanalysis.objlist.TagItem;
import org.jdbg.gui.util.InfoBorder;
import org.jgrapht.Graph;
import org.jgrapht.ext.JGraphXAdapter;
import org.jgrapht.graph.DefaultDirectedGraph;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.Map;

public class ObjectInfo extends JPanel {


    public ObjectInfo(TagItem tagItem, FieldResponseData fields, Map<Integer, SubGraphData> graphData) {
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));

        JPanel panel = new JPanel();
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));
        panel.setBorder(new InfoBorder(tagItem.toString()));

        if(fields.value==null) {
            panel.add(new ObjectStringInfo("Object Value: N/A"));
        } else {
            ObjectInfoInput input = new ObjectInfoInput("Object Value",  fields.value, "Set Value");

            input.addActionListener(new ActionListener() {
                @Override
                public void actionPerformed(ActionEvent e) {
                    CoreInterface.getInstance().setObjectValue(tagItem, input.getText());
                }
            });

            panel.add(input);
        }


        panel.add(new ObjectStringInfo("Object Tag: " + tagItem.getTag()));

        panel.setMaximumSize(new Dimension(10000, 500));
        add(panel);


        String[][] str = new String[fields.fields.size()][3];

        int i = 0;
        for(Map.Entry<String, FieldData> data : fields.fields.entrySet()) {
            str[i][0]=data.getValue().signature;
            str[i][1]=data.getKey();
            str[i][2]=data.getValue().value;
            i++;
        }

        JTable table = new JTable(str, new String[] {"Signature", "Name", "Value"});
        JScrollPane scrollPane = new JScrollPane(table, ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED,
                ScrollPaneConstants.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        scrollPane.setBorder(new InfoBorder("Fields"));
        table.setFont(new Font(getFont().getName(), getFont().getStyle(), getFont().getSize()+4));



        scrollPane.setPreferredSize(new Dimension(getWidth(), 100));

        add(scrollPane);
        createGraph(graphData);
    }

    void createGraph(Map<Integer, SubGraphData> graphData) {
        Graph<HeapVertex, HeapEdge> g = new DefaultDirectedGraph<>(HeapEdge.class);

        for(Map.Entry<Integer, SubGraphData> entry : graphData.entrySet()) {
            g.addVertex(new HeapVertex(entry.getKey(), entry.getValue().origin, entry.getValue().isRoot));

        }

        for(Map.Entry<Integer, SubGraphData> entry : graphData.entrySet()) {
            for(int i = 0 ; i < entry.getValue().adj.length; i++) {
                if(entry.getValue().adj[i] != 0)
                    g.addEdge(new HeapVertex(entry.getValue().adj[i]), new HeapVertex(entry.getKey()), new HeapEdge(entry.getValue().relationshipType[i]));
            }
        }


        mxConstants.DEFAULT_FONTSIZE = getFont().getSize()+3;
        JGraphXAdapter<HeapVertex, HeapEdge> jGraphXAdapter = new JGraphXAdapter<>(g);



        style(jGraphXAdapter);


        mxGraphComponent component = new mxGraphComponent(jGraphXAdapter);
        component.setPanning(true);
        component.setZoomPolicy(mxGraphComponent.ZOOM_POLICY_PAGE);
        //component.setMaximumSize(new Dimension(500, 700));
        component.setBorder(new InfoBorder("Heap Relationship"));
        component.setConnectable(false);
        component.getGraph().setAllowDanglingEdges(false);

        add(component);

        /*
        mxCompactTreeLayout layout = new mxCompactTreeLayout(jGraphXAdapter);
        layout.setHorizontal(false);
        layout.setEdgeRouting(false);
        layout.setNodeDistance(50);
        layout.setLevelDistance(30);
        */

        mxHierarchicalLayout layout = new mxHierarchicalLayout(jGraphXAdapter);
        layout.setDisableEdgeStyle(true);
        layout.execute(jGraphXAdapter.getDefaultParent());

       component.setPreferredSize(new Dimension(getWidth(), 700));
    }

    void style(JGraphXAdapter<HeapVertex, HeapEdge> jGraphXAdapter) {
        mxStylesheet stylesheet = jGraphXAdapter.getStylesheet();
        Map<String, Object> vertexStyle = stylesheet.getDefaultVertexStyle();

        vertexStyle.put(mxConstants.STYLE_FONTFAMILY, getFont().getFamily());
        vertexStyle.put(mxConstants.STYLE_ROUNDED, true);
        vertexStyle.put(mxConstants.STYLE_OPACITY, 20);
        vertexStyle.put(mxConstants.STYLE_FONTCOLOR, Util.convertColorToHex(UIManager.getColor("TextField.foreground"))); // Red color
        vertexStyle.put(mxConstants.STYLE_SPACING, 15);
        vertexStyle.put(mxConstants.STYLE_SPACING_BOTTOM, 15);
        vertexStyle.put(mxConstants.STYLE_SPACING_TOP, 15);
        vertexStyle.put(mxConstants.STYLE_SPACING_LEFT, 15);
        vertexStyle.put(mxConstants.STYLE_SPACING_RIGHT, 15);


        for(Object obj : jGraphXAdapter.getChildVertices(jGraphXAdapter.getDefaultParent())) {
            mxCell c = (mxCell) obj;
            mxGeometry geo = c.getGeometry();
            if(c.isVertex()) {
                geo.setWidth(geo.getWidth()+30);
                geo.setHeight(geo.getHeight()+15);
            }

            if(((HeapVertex)c.getValue()).isRoot()) {
                jGraphXAdapter.setCellStyle("fillColor=green", new Object[]{c});
            }
        }


        java.util.Map<String, Object> edgeStyle = stylesheet.getDefaultEdgeStyle();
        edgeStyle.put(mxConstants.STYLE_FONTFAMILY, getFont().getFamily());
        edgeStyle.put(mxConstants.STYLE_STROKECOLOR, Util.convertColorToHex(UIManager.getColor("TextField.foreground"))); // Red color
        edgeStyle.put(mxConstants.STYLE_STROKEWIDTH, 2);
        edgeStyle.put(mxConstants.STYLE_FONTCOLOR, Util.convertColorToHex(UIManager.getColor("TextField.foreground"))); // Red color

    }
}
