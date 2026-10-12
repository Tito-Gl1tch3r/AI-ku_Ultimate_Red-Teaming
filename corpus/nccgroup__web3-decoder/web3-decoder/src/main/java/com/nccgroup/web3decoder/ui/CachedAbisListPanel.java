// File: CachedAbisListPanel.java
package com.nccgroup.web3decoder.ui;

import com.nccgroup.web3decoder.abi.AbiProvider;
import com.nccgroup.web3decoder.persistence.CachedAbis;
import com.nccgroup.web3decoder.persistence.ChainInfo;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;

import burp.api.montoya.MontoyaApi;

import javax.swing.*;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.TableColumn;
import java.awt.*;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.List;
import java.util.Optional;
import javax.swing.event.ListSelectionListener;
import javax.swing.event.ListSelectionEvent;

/**
 * A JPanel containing the Cached ABIs JTable and "Add Cached ABI" and "Remove ABI" buttons.
 * It notifies listeners when a Cached ABI is selected.
 */
public class CachedAbisListPanel extends JPanel implements AbiEditorPanel.AbiSaveListener {
    private final MontoyaApi api;
    private final ExtensionConfig config;
    private final CachedAbis cachedAbis;

    private final CachedAbisTableModel cachedAbisTableModel;
    private final JTable cachedAbisTable;
    private JButton addCachedAbiButton;
    private JButton removeAbiButton;

    /**
     * Listener interface for ABI selection events.
     */
    public interface AbiSelectionListener {
        void onAbiSelected(int chainId, String contractAddress, String abi);
    }

    private AbiSelectionListener abiSelectionListener;

    /**
     * Sets the ABISelectionListener.
     *
     * @param listener The listener to set.
     */
    public void setAbiSelectionListener(AbiSelectionListener listener) {
        this.abiSelectionListener = listener;
    }

    /**
     * Constructs the CachedAbisListPanel.
     *
     * @param api        The Montoya API instance.
     * @param config     The ExtensionConfig instance for data access.
     * @param cachedAbis The CachedAbis instance for managing cached ABIs.
     */
    public CachedAbisListPanel(MontoyaApi api, ExtensionConfig config, CachedAbis cachedAbis) {
        this.api = api;
        this.config = config;
        this.cachedAbis = cachedAbis;
        this.cachedAbisTableModel = new CachedAbisTableModel();
        this.cachedAbisTable = new JTable(cachedAbisTableModel);
        initializeUI();
        loadData();
    }

    /**
     * Initializes the UI components for the CachedAbisListPanel.
     */
    private void initializeUI() {
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));

        // Cached ABIs Table Setup
        cachedAbisTable.setFillsViewportHeight(true);
        cachedAbisTable.setAutoCreateRowSorter(true);
        cachedAbisTable.setRowHeight(25);
        cachedAbisTable.setAutoResizeMode(JTable.AUTO_RESIZE_ALL_COLUMNS);
        cachedAbisTable.setBorder(BorderFactory.createLineBorder(Color.GRAY));

        // Define columns for Cached ABIs Table
        String[] cachedAbiColumnNames = {"Chain ID", "Contract Address"};
        cachedAbisTableModel.setColumnNames(cachedAbiColumnNames);

        // Set column widths
        TableColumn chainIdColumn = cachedAbisTable.getColumnModel().getColumn(0);
        chainIdColumn.setPreferredWidth(80);

        TableColumn contractAddressColumn = cachedAbisTable.getColumnModel().getColumn(1);
        contractAddressColumn.setPreferredWidth(200);

        JScrollPane cachedAbisScrollPane = new JScrollPane(cachedAbisTable);
        cachedAbisScrollPane.setAlignmentX(Component.CENTER_ALIGNMENT);
        add(cachedAbisScrollPane);
        add(Box.createRigidArea(new Dimension(0, 5))); // Spacing

        // Buttons Panel
        JPanel buttonsPanel = new JPanel();
        buttonsPanel.setLayout(new FlowLayout(FlowLayout.CENTER, 10, 0));

        // Add Cached ABI Button
        addCachedAbiButton = new JButton("Add Cached ABI");
        addCachedAbiButton.setToolTipText("Click to add a new cached ABI by providing Chain ID, Contract Address, and optionally an ABI.");
        buttonsPanel.add(addCachedAbiButton);

        // Remove ABI Button
        removeAbiButton = new JButton("Remove ABI");
        removeAbiButton.setToolTipText("Remove the selected cached ABI.");
        removeAbiButton.setEnabled(false); // Initially disabled
        buttonsPanel.add(removeAbiButton);

        add(buttonsPanel);

        // Action Listener for Add Cached ABI Button
        addCachedAbiButton.addActionListener(e -> showAddCachedAbiDialog());

        // Action Listener for Remove ABI Button
        removeAbiButton.addActionListener(e -> removeSelectedAbi());

        // Selection Listener for Cached ABIs Table
        cachedAbisTable.getSelectionModel().addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) {
                removeAbiButton.setEnabled(cachedAbisTable.getSelectedRowCount() > 0);
                displaySelectedAbi();
            }
        });

        // Add double-click functionality to the "Contract Address" column
        addDoubleClickListener();
    }

    /**
     * Adds a mouse listener to the "Contract Address" column to handle double-click events.
     */
    private void addDoubleClickListener() {
        cachedAbisTable.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                // Detect double-click
                if (e.getClickCount() == 2 && !e.isConsumed()) {
                    e.consume();

                    // Get the point where the click occurred
                    Point point = e.getPoint();

                    // Get the row and column index of the click
                    int row = cachedAbisTable.rowAtPoint(point);
                    int column = cachedAbisTable.columnAtPoint(point);

                    // Check if the double-click is on the "Contract Address" column
                    int contractAddressColumnIndex = cachedAbisTableModel.getColumnIndex("Contract Address");
                    if (column == contractAddressColumnIndex) {
                        // Select the row
                        cachedAbisTable.setRowSelectionInterval(row, row);

                        // Display the selected ABI
                        displaySelectedAbi();
                    }
                }
            }
        });
    }

    /**
     * Loads cached ABIs data from the cache into the table model and adjusts table size.
     */
    public void loadData() {
        List<CachedAbis.ABIEntry> cachedAbisList = cachedAbis.getAllCachedABIs();
        cachedAbisTableModel.setCachedAbis(cachedAbisList);
        adjustTableHeight();
    }

    /**
     * Adjusts the Cached ABIs table's preferred height based on the number of rows.
     */
    private void adjustTableHeight() {
        int rowCount = cachedAbisTable.getRowCount();
        int rowHeight = cachedAbisTable.getRowHeight();
        int tableHeaderHeight = cachedAbisTable.getTableHeader().getPreferredSize().height + 10;
        int maxVisibleRows = 20;
        int visibleRows = Math.min(rowCount, maxVisibleRows);
        int newHeight = (rowHeight * visibleRows) + tableHeaderHeight;

        int width = cachedAbisTable.getPreferredScrollableViewportSize().width;

        JScrollPane scrollPane = (JScrollPane) cachedAbisTable.getParent().getParent();
        scrollPane.setPreferredSize(new Dimension(width, newHeight));
        scrollPane.setMaximumSize(new Dimension(width, newHeight));

        revalidate();
        repaint();
    }

    /**
     * Displays a dialog to add a new cached ABI with an optional ABI input.
     */
    private void showAddCachedAbiDialog() {
        JTextField chainIdField = new JTextField();
        JTextField contractAddressField = new JTextField();

        // ABI input area (optional)
        JTextArea abiTextArea = new JTextArea(10, 30);
        abiTextArea.setLineWrap(true);
        abiTextArea.setWrapStyleWord(true);
        JScrollPane abiScrollPane = new JScrollPane(abiTextArea);

        Object[] message = {
                "Add New Cached ABI",
                "Chain ID (integer):", chainIdField,
                "Contract Address:", contractAddressField,
                "ABI (JSON format - Optional):", abiScrollPane
        };

        int option = JOptionPane.showConfirmDialog(this, message, "Add Cached ABI", JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE);
        if (option == JOptionPane.OK_OPTION) {
            try {
                int chainId = Integer.parseInt(chainIdField.getText().trim());
                String contractAddress = contractAddressField.getText().trim().toLowerCase();
                String abi = abiTextArea.getText().trim();

                if (contractAddress.isEmpty()) {
                    JOptionPane.showMessageDialog(this, "Contract Address cannot be empty.", "Input Error", JOptionPane.ERROR_MESSAGE);
                    return;
                }

                // Validate Contract Address format
                if (!contractAddress.startsWith("0x") || contractAddress.length() != 42) {
                    JOptionPane.showMessageDialog(this, "Invalid Contract Address format. It should start with '0x' and be 42 characters long.", "Input Error", JOptionPane.ERROR_MESSAGE);
                    return;
                }

                // Check if the chain exists
                ChainInfo chain = config.getChain(chainId);
                if (chain == null) {
                    JOptionPane.showMessageDialog(this, "Chain ID " + chainId + " does not exist. Please add the chain first.", "Invalid Chain ID", JOptionPane.ERROR_MESSAGE);
                    return;
                }

                if (!abi.isEmpty()) {
                    // User provided ABI manually
                    // Validate that the ABI is valid JSON
                    if (!isValidJson(abi)) {
                        JOptionPane.showMessageDialog(this, "Invalid ABI format. Please ensure it is valid JSON.", "Input Error", JOptionPane.ERROR_MESSAGE);
                        return;
                    }

                    // Cache the ABI
                    cachedAbis.saveAbi(chainId, contractAddress, abi);

                    // Reload the cached ABIs table
                    loadData();

                    JOptionPane.showMessageDialog(this, "ABI entered and cached successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
                    api.logging().logToOutput("Manually cached ABI for contract: " + contractAddress + " on chain ID: " + chainId + ".");
                } else {
                    // No ABI provided; fetch from Etherscan
                    if (chain.getExplorer() == null || chain.getExplorer().trim().isEmpty()) {
                        JOptionPane.showMessageDialog(this, "This chain has no explorer configured. Please paste ABI JSON manually.", "Manual ABI Required", JOptionPane.INFORMATION_MESSAGE);
                        return;
                    }
                    AbiProvider abiProvider = new AbiProvider(api, chainId, chain.getExplorer(), config.resolveExplorerAPIKey(chain), config);
                    
                    // Create a SwingWorker to fetch and cache the ABI asynchronously
                    SwingWorker<Optional<String>, Void> worker = new SwingWorker<Optional<String>, Void>() {
                        @Override
                        protected Optional<String> doInBackground() throws Exception {
                            // Fetch the ABI using EtherscanAPI
                            String abi = abiProvider.getAbi(contractAddress);
                            return Optional.ofNullable(abi);
                        }

                        @Override
                        protected void done() {
                            try {
                                Optional<String> abiOptional = get();
                                if (abiOptional.isPresent()) {
                                    // No need to cache the ABI. the abiProvider caches it for us
                                    //cachedAbis.saveAbi(chainId, contractAddress, abiOptional.get());

                                    // Reload the cached ABIs table
                                    loadData();

                                    JOptionPane.showMessageDialog(CachedAbisListPanel.this, "ABI fetched and cached successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
                                    api.logging().logToOutput("Cached ABI for contract: " + contractAddress + " on chain ID: " + chainId + ".");
                                } else {
                                    JOptionPane.showMessageDialog(CachedAbisListPanel.this, "Failed to fetch ABI for the given contract address.", "Fetch Error", JOptionPane.ERROR_MESSAGE);
                                    api.logging().logToError("Failed to fetch ABI for contract: " + contractAddress + ".");
                                }
                            } catch (Exception ex) {
                                JOptionPane.showMessageDialog(CachedAbisListPanel.this, "An error occurred while fetching the ABI.", "Error", JOptionPane.ERROR_MESSAGE);
                                api.logging().logToError("Error fetching ABI: " + ex.getMessage());
                            }
                        }
                    };

                    worker.execute();
                }
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(this, "Chain ID must be an integer.", "Input Error", JOptionPane.ERROR_MESSAGE);
            }
        }
    }

    /**
     * Utility method to validate JSON strings.
     *
     * @param jsonStr The JSON string to validate.
     * @return true if valid JSON, false otherwise.
     */
    private boolean isValidJson(String jsonStr) {
        try {
            new com.fasterxml.jackson.databind.ObjectMapper().readTree(jsonStr);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * Displays the selected ABI in the ABI Editor by notifying the listener.
     */
    private void displaySelectedAbi() {
        int selectedRow = cachedAbisTable.getSelectedRow();
        if (selectedRow == -1) {
            if (abiSelectionListener != null) {
                abiSelectionListener.onAbiSelected(-1, null, "");
            }
            return;
        }

        int modelRow = cachedAbisTable.convertRowIndexToModel(selectedRow);
        CachedAbis.ABIEntry entry = cachedAbisTableModel.getAbiEntryAt(modelRow);

        if (entry == null) {
            if (abiSelectionListener != null) {
                abiSelectionListener.onAbiSelected(-1, null, "");
            }
            return;
        }

        try {
            String cachedAbi = cachedAbis.getAbi(entry.getChainId(), entry.getContractAddress());
            if (cachedAbi != null) {
                if (abiSelectionListener != null) {
                    abiSelectionListener.onAbiSelected(entry.getChainId(), entry.getContractAddress(), cachedAbi);
                }
            } else {
                if (abiSelectionListener != null) {
                    abiSelectionListener.onAbiSelected(entry.getChainId(), entry.getContractAddress(), "ABI not found.");
                }
            }
        } catch (Exception e) {
            if (abiSelectionListener != null) {
                abiSelectionListener.onAbiSelected(entry.getChainId(), entry.getContractAddress(), "Error retrieving ABI: " + e.getMessage());
            }
            api.logging().logToError("Error retrieving ABI: " + e.getMessage());
        }
    }

    /**
     * Removes every selected ABI from the cache.
     */
    private void removeSelectedAbi() {
        int[] selectedRows = cachedAbisTable.getSelectedRows();
        if (selectedRows.length == 0) {
            JOptionPane.showMessageDialog(this, "Please select an ABI to remove.", "No Selection", JOptionPane.WARNING_MESSAGE);
            return;
        }

        // Snapshot entries before mutating the model so view-row → model-row indices stay valid.
        java.util.List<CachedAbis.ABIEntry> toRemove = new java.util.ArrayList<>(selectedRows.length);
        for (int viewRow : selectedRows) {
            int modelRow = cachedAbisTable.convertRowIndexToModel(viewRow);
            CachedAbis.ABIEntry entry = cachedAbisTableModel.getAbiEntryAt(modelRow);
            if (entry != null) {
                toRemove.add(entry);
            }
        }
        if (toRemove.isEmpty()) return;

        String confirmMsg = toRemove.size() == 1
                ? "Are you sure you want to remove the selected ABI?"
                : "Are you sure you want to remove " + toRemove.size() + " selected ABIs?";
        int confirm = JOptionPane.showConfirmDialog(this, confirmMsg, "Confirm Removal", JOptionPane.YES_NO_OPTION);
        if (confirm != JOptionPane.YES_OPTION) return;

        for (CachedAbis.ABIEntry entry : toRemove) {
            cachedAbis.removeAbi(entry.getChainId(), entry.getContractAddress());
            api.logging().logToOutput("Removed cached ABI for contract: " + entry.getContractAddress() + " on chain ID: " + entry.getChainId() + ".");
        }

        loadData();

        String doneMsg = toRemove.size() == 1
                ? "ABI removed successfully."
                : toRemove.size() + " ABIs removed successfully.";
        JOptionPane.showMessageDialog(this, doneMsg, "Success", JOptionPane.INFORMATION_MESSAGE);

        if (abiSelectionListener != null) {
            abiSelectionListener.onAbiSelected(-1, null, "");
        }
    }

    /**
     * Handles the ABI save event from the AbiEditorPanel.
     *
     * @param chainId         The chain ID of the ABI.
     * @param contractAddress The contract address of the ABI.
     * @param abi             The edited ABI string.
     */
    @Override
    public void onAbiSave(int chainId, String contractAddress, String abi) {
        // Validate that the ABI is valid JSON
        if (!isValidJson(abi)) {
            JOptionPane.showMessageDialog(this, "Invalid ABI format. Please ensure it is valid JSON.", "Input Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        // Save the edited ABI
        cachedAbis.saveAbi(chainId, contractAddress, abi);

        // Optionally, refresh the data or update the UI as needed
        api.logging().logToOutput("Updated ABI for contract: " + contractAddress + " on chain ID: " + chainId + ".");
        JOptionPane.showMessageDialog(this, "ABI saved successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
    }

    /**
     * A custom TableModel for the Cached ABIs table.
     */
    private class CachedAbisTableModel extends AbstractTableModel {
        private String[] columnNames = {"Chain ID", "Contract Address"};
        private List<CachedAbis.ABIEntry> cachedAbis;

        /**
         * Sets the column names for the table.
         *
         * @param columnNames An array of column names.
         */
        public void setColumnNames(String[] columnNames) {
            this.columnNames = columnNames;
            fireTableStructureChanged();
        }

        /**
         * Sets the list of cached ABIs to be displayed in the table.
         *
         * @param cachedAbis A list of ABIEntry objects.
         */
        public void setCachedAbis(List<CachedAbis.ABIEntry> cachedAbis) {
            this.cachedAbis = cachedAbis;
            fireTableDataChanged();
        }

        @Override
        public int getRowCount() {
            return cachedAbis == null ? 0 : cachedAbis.size();
        }

        @Override
        public int getColumnCount() {
            return columnNames.length;
        }

        @Override
        public String getColumnName(int col) {
            return columnNames[col];
        }

        @Override
        public Object getValueAt(int row, int col) {
            CachedAbis.ABIEntry entry = cachedAbis.get(row);
            switch (col) {
                case 0:
                    return entry.getChainId();
                case 1:
                    return entry.getContractAddress();
                default:
                    return null;
            }
        }

        @Override
        public boolean isCellEditable(int row, int col) {
            // All cells are non-editable
            return false;
        }

        @Override
        public Class<?> getColumnClass(int col) {
            if (col == 0) {
                return Integer.class;
            }
            return String.class;
        }

        /**
         * Retrieves the ABIEntry object at the specified row.
         *
         * @param row The row index.
         * @return The corresponding ABIEntry object.
         */
        public CachedAbis.ABIEntry getAbiEntryAt(int row) {
            if (cachedAbis == null || row < 0 || row >= cachedAbis.size()) {
                return null;
            }
            return cachedAbis.get(row);
        }

        /**
         * Gets the index of a column by its name.
         *
         * @param columnName The name of the column.
         * @return The index of the column, or -1 if not found.
         */
        public int getColumnIndex(String columnName) {
            for (int i = 0; i < columnNames.length; i++) {
                if (columnNames[i].equals(columnName)) {
                    return i;
                }
            }
            return -1;
        }
    }
}
