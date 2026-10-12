package com.nccgroup.web3decoder.ui;

import com.nccgroup.web3decoder.detection.DetectedAbi;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;

import burp.api.montoya.MontoyaApi;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.TableColumn;
import java.awt.Color;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Point;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.List;

/**
 * A JPanel showing every ABI detected from passive scanning, with the URL where it was
 * first seen and the number of function selectors it carries. Mirrors the
 * {@link CachedAbisListPanel} shape so the two can sit side-by-side under a single
 * "Cached / Detected ABIs" section.
 */
public class DetectedAbisListPanel extends JPanel {

    private final MontoyaApi api;
    private final DetectedAbiStore store;
    private final DetectedAbisTableModel tableModel;
    private final JTable table;
    private JButton removeButton;

    /**
     * Fired when a detected-ABI row is selected (or cleared by selecting nothing).
     * The {@code abi} argument carries the canonical JSON ready for display.
     */
    public interface DetectedAbiSelectionListener {
        void onDetectedAbiSelected(String fingerprint, String firstSeenUrl, String abi);
    }

    private DetectedAbiSelectionListener selectionListener;

    public void setSelectionListener(DetectedAbiSelectionListener listener) {
        this.selectionListener = listener;
    }

    public DetectedAbisListPanel(MontoyaApi api, DetectedAbiStore store) {
        this.api = api;
        this.store = store;
        this.tableModel = new DetectedAbisTableModel();
        this.table = new JTable(tableModel);
        initializeUI();
        loadData();
    }

    private void initializeUI() {
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));

        table.setFillsViewportHeight(true);
        table.setAutoCreateRowSorter(true);
        table.setRowHeight(25);
        table.setAutoResizeMode(JTable.AUTO_RESIZE_LAST_COLUMN);
        table.setBorder(BorderFactory.createLineBorder(Color.GRAY));

        TableColumn fpCol = table.getColumnModel().getColumn(0);
        fpCol.setPreferredWidth(110);
        TableColumn methodsCol = table.getColumnModel().getColumn(1);
        methodsCol.setPreferredWidth(70);
        TableColumn urlCol = table.getColumnModel().getColumn(2);
        urlCol.setPreferredWidth(300);

        JScrollPane scrollPane = new JScrollPane(table);
        scrollPane.setAlignmentX(Component.CENTER_ALIGNMENT);
        add(scrollPane);
        add(Box.createRigidArea(new Dimension(0, 5)));

        JPanel buttonsPanel = new JPanel(new FlowLayout(FlowLayout.CENTER, 10, 0));
        removeButton = new JButton("Remove ABI");
        removeButton.setToolTipText("Remove the selected detected ABI from the pool.");
        removeButton.setEnabled(false);
        buttonsPanel.add(removeButton);
        add(buttonsPanel);

        removeButton.addActionListener(e -> removeSelected());

        table.getSelectionModel().addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) {
                removeButton.setEnabled(table.getSelectedRowCount() > 0);
                fireSelection();
            }
        });

        table.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if (e.getClickCount() == 2 && !e.isConsumed()) {
                    e.consume();
                    Point point = e.getPoint();
                    int row = table.rowAtPoint(point);
                    if (row >= 0) {
                        table.setRowSelectionInterval(row, row);
                        fireSelection();
                    }
                }
            }
        });
    }

    /** Reload the list from the store and adjust the table's preferred height. */
    public void loadData() {
        tableModel.setEntries(store.snapshot());
        adjustTableHeight();
    }

    private void adjustTableHeight() {
        int rowCount = table.getRowCount();
        int rowHeight = table.getRowHeight();
        int headerHeight = table.getTableHeader().getPreferredSize().height + 10;
        int maxVisibleRows = 20;
        int visibleRows = Math.min(rowCount, maxVisibleRows);
        int newHeight = (rowHeight * visibleRows) + headerHeight;
        int width = table.getPreferredScrollableViewportSize().width;

        JScrollPane scrollPane = (JScrollPane) table.getParent().getParent();
        scrollPane.setPreferredSize(new Dimension(width, newHeight));
        scrollPane.setMaximumSize(new Dimension(width, newHeight));

        revalidate();
        repaint();
    }

    private void fireSelection() {
        if (selectionListener == null) return;
        int selectedRow = table.getSelectedRow();
        if (selectedRow == -1) {
            selectionListener.onDetectedAbiSelected(null, null, "");
            return;
        }
        int modelRow = table.convertRowIndexToModel(selectedRow);
        DetectedAbiStore.Entry entry = tableModel.entryAt(modelRow);
        if (entry == null) {
            selectionListener.onDetectedAbiSelected(null, null, "");
            return;
        }
        selectionListener.onDetectedAbiSelected(
                entry.abi().fingerprint(), entry.firstSeenUrl(), entry.abi().canonicalJson());
    }

    private void removeSelected() {
        int[] selectedRows = table.getSelectedRows();
        if (selectedRows.length == 0) return;

        // Snapshot entries before mutating the model so row indices stay valid.
        java.util.List<DetectedAbiStore.Entry> toRemove = new java.util.ArrayList<>(selectedRows.length);
        for (int viewRow : selectedRows) {
            int modelRow = table.convertRowIndexToModel(viewRow);
            DetectedAbiStore.Entry entry = tableModel.entryAt(modelRow);
            if (entry != null) {
                toRemove.add(entry);
            }
        }
        if (toRemove.isEmpty()) return;

        String confirmMsg = toRemove.size() == 1
                ? "Remove the selected detected ABI from the pool?"
                : "Remove " + toRemove.size() + " selected detected ABIs from the pool?";
        int confirm = JOptionPane.showConfirmDialog(this, confirmMsg, "Confirm Removal", JOptionPane.YES_NO_OPTION);
        if (confirm != JOptionPane.YES_OPTION) return;

        boolean changed = false;
        for (DetectedAbiStore.Entry entry : toRemove) {
            if (store.remove(entry.abi().fingerprint())) {
                api.logging().logToOutput("Removed detected ABI " + entry.abi().fingerprint());
                changed = true;
            }
        }
        if (changed) {
            loadData();
            if (selectionListener != null) {
                selectionListener.onDetectedAbiSelected(null, null, "");
            }
        }
    }

    private static class DetectedAbisTableModel extends AbstractTableModel {
        private static final String[] COLUMN_NAMES = {"Fingerprint", "Methods", "First seen at"};
        private List<DetectedAbiStore.Entry> entries = List.of();

        public void setEntries(List<DetectedAbiStore.Entry> entries) {
            this.entries = entries;
            fireTableDataChanged();
        }

        public DetectedAbiStore.Entry entryAt(int row) {
            if (row < 0 || row >= entries.size()) return null;
            return entries.get(row);
        }

        @Override public int getRowCount()   { return entries.size(); }
        @Override public int getColumnCount(){ return COLUMN_NAMES.length; }
        @Override public String getColumnName(int col) { return COLUMN_NAMES[col]; }

        @Override
        public Object getValueAt(int row, int col) {
            DetectedAbiStore.Entry e = entries.get(row);
            DetectedAbi abi = e.abi();
            switch (col) {
                case 0: {
                    String fp = abi.fingerprint();
                    return fp.length() > 12 ? fp.substring(0, 12) + "…" : fp;
                }
                case 1: return abi.selectors().size();
                case 2: return e.firstSeenUrl();
                default: return null;
            }
        }

        @Override public boolean isCellEditable(int row, int col) { return false; }

        @Override
        public Class<?> getColumnClass(int col) {
            return col == 1 ? Integer.class : String.class;
        }
    }
}
