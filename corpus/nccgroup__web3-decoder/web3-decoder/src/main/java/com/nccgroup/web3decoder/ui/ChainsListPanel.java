// File: ChainsListPanel.java
package com.nccgroup.web3decoder.ui;

import com.nccgroup.web3decoder.persistence.ChainInfo;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import burp.api.montoya.MontoyaApi;

import javax.swing.*;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.table.TableColumn;
import java.awt.*;
import java.awt.event.FocusAdapter;
import java.awt.event.FocusEvent;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.List;
import java.util.Map;

/**
 * A JPanel containing a JTable to display and manage blockchain chains.
 * It allows users to add new chains, remove existing ones, and edit API keys securely.
 * The table adjusts its height based on the number of chains to optimize space usage.
 *
 * Enhancements:
 * - Removed the "Edit" button from each row.
 * - Added a single "Edit API Key for Selected Chain" button below the table.
 * - Enhanced API Key Status visibility with bold colored text.
 * - Centered the buttons below the table.
 * - Maintained table borders and alternating row background colors.
 * - Reduced spacing between the table and the buttons.
 * - Added double-click functionality on the "API Key Status" column to edit API keys.
 */
public class ChainsListPanel extends JPanel {
    private final ExtensionConfig config;
    private final MontoyaApi api;
    private final ChainsTableModel tableModel;
    private final JTable table;
    private JButton addChainButton;
    private JButton editChainButton;
    private JButton removeChainButton;
    private JButton editApiKeyButton;
    private JPasswordField sharedApiKeyField;
    private JLabel sharedApiKeyStatusLabel;
    private JScrollPane scrollPane;

    /**
     * Constructs the ChainsListPanel.
     *
     * @param api    The Montoya API instance.
     * @param config The ExtensionConfig instance for data access.
     */
    public ChainsListPanel(MontoyaApi api, ExtensionConfig config) {
        this.api = api;
        this.config = config;
        this.tableModel = new ChainsTableModel();
        this.table = new JTable(tableModel);
        initializeUI();
        loadData();
    }

    /**
     * Initializes the UI components. Layout:
     * CENTER = scrollable chains table.
     * SOUTH  = vertically stacked: shared-Etherscan-key row, then a single
     *          docked action toolbar (Add / Edit / Remove ... Edit API key).
     */
    private void initializeUI() {
        setLayout(new BorderLayout(0, 6));

        // Columns: Chain ID, Name, Explorer, Mode, API Key
        String[] columnNames = {"Chain ID", "Name", "Explorer", "Mode", "API Key"};
        tableModel.setColumnNames(columnNames);

        table.setFillsViewportHeight(true);
        table.setAutoCreateRowSorter(true);
        table.setRowHeight(25);
        table.setAutoResizeMode(JTable.AUTO_RESIZE_ALL_COLUMNS);

        TableColumn chainIdColumn = table.getColumnModel().getColumn(0);
        chainIdColumn.setPreferredWidth(80);
        TableColumn nameColumn = table.getColumnModel().getColumn(1);
        nameColumn.setPreferredWidth(150);
        TableColumn explorerColumn = table.getColumnModel().getColumn(2);
        explorerColumn.setPreferredWidth(200);
        TableColumn modeColumn = table.getColumnModel().getColumn(3);
        modeColumn.setPreferredWidth(120);
        TableColumn apiKeyStatusColumn = table.getColumnModel().getColumn(4);
        apiKeyStatusColumn.setPreferredWidth(150);
        apiKeyStatusColumn.setCellRenderer(new ApiKeyStatusRenderer());

        scrollPane = new JScrollPane(table);
        add(scrollPane, BorderLayout.CENTER);

        addDoubleClickListener();

        // ---- South stack: shared key row + action toolbar ----
        JPanel south = new JPanel();
        south.setLayout(new BoxLayout(south, BoxLayout.Y_AXIS));
        south.setOpaque(false);

        // Shared Etherscan key row (inline with table, left-aligned).
        JPanel sharedKeyPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 0));
        sharedKeyPanel.setOpaque(false);
        JLabel sharedKeyLabel = new JLabel("Shared Etherscan key:");
        sharedApiKeyField = new JPasswordField(28);
        sharedApiKeyField.setText(config.getSharedEtherscanApiKey());
        sharedApiKeyField.setToolTipText("Used by Etherscan-family chains unless a per-chain override is set.");
        sharedApiKeyStatusLabel = new JLabel();
        updateSharedKeyStatusLabel();
        sharedApiKeyField.addActionListener(e -> persistSharedApiKeyFromField());
        sharedApiKeyField.addFocusListener(new FocusAdapter() {
            @Override
            public void focusLost(FocusEvent e) {
                persistSharedApiKeyFromField();
            }
        });
        sharedKeyPanel.add(sharedKeyLabel);
        sharedKeyPanel.add(sharedApiKeyField);
        sharedKeyPanel.add(sharedApiKeyStatusLabel);
        sharedKeyPanel.setAlignmentX(Component.LEFT_ALIGNMENT);
        south.add(sharedKeyPanel);

        // Action toolbar: left-aligned action group + right-aligned API-key button.
        JPanel toolbar = new JPanel();
        toolbar.setLayout(new BoxLayout(toolbar, BoxLayout.X_AXIS));
        toolbar.setOpaque(true);
        toolbar.setBackground(Web3UiTheme.panelHeaderBg());
        toolbar.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(1, 0, 0, 0, Web3UiTheme.dividerColor()),
                BorderFactory.createEmptyBorder(6, 8, 6, 8)));
        addChainButton = new JButton("Add chain");
        editChainButton = new JButton("Edit selected");
        removeChainButton = new JButton("Remove selected");
        editApiKeyButton = new JButton("Edit API key");

        addChainButton.setToolTipText("Add a new blockchain chain.");
        editChainButton.setToolTipText("Edit Name/Explorer for the selected chain.");
        removeChainButton.setToolTipText("Remove the selected blockchain chain.");
        editApiKeyButton.setToolTipText("Edit the API key for the selected chain.");

        toolbar.add(addChainButton);
        toolbar.add(Box.createHorizontalStrut(6));
        toolbar.add(editChainButton);
        toolbar.add(Box.createHorizontalStrut(6));
        toolbar.add(removeChainButton);
        toolbar.add(Box.createHorizontalGlue());
        toolbar.add(editApiKeyButton);
        toolbar.setAlignmentX(Component.LEFT_ALIGNMENT);
        south.add(toolbar);

        add(south, BorderLayout.SOUTH);

        addChainButton.addActionListener(e -> showAddChainDialog());
        editChainButton.addActionListener(e -> editSelectedChain());
        removeChainButton.addActionListener(e -> removeSelectedChain());
        editApiKeyButton.addActionListener(e -> editApiKeyForSelectedChain());
    }

    /**
     * Adds a mouse listener to the "API Key Status" column to handle double-click events.
     */
    private void addDoubleClickListener() {
        table.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                // Detect double-click
                if (e.getClickCount() == 2 && !e.isConsumed()) {
                    e.consume();

                    // Get the point where the click occurred
                    Point point = e.getPoint();

                    // Get the row and column index of the click
                    int row = table.rowAtPoint(point);
                    int column = table.columnAtPoint(point);

                    // Check if the double-click is on the "API Key" column
                    int apiKeyStatusColumnIndex = tableModel.getColumnIndex("API Key");
                    if (column == apiKeyStatusColumnIndex) {
                        // Select the row
                        table.setRowSelectionInterval(row, row);

                        // Trigger the edit API key action
                        editApiKeyForSelectedChain();
                    }
                }
            }
        });
    }

    /**
     * Loads data from the ExtensionConfig into the table model and adjusts table size.
     */
    public void loadData() {
        Map<Integer, ChainInfo> chainsMap = config.getAllChains();
        List<ChainInfo> chainsList = List.copyOf(chainsMap.values());
        tableModel.setChains(chainsList);
        adjustTableHeight();
    }

    /**
     * Under the new BorderLayout the scroll pane fills the panel's CENTER
     * region and is sized by the surrounding split pane. We only revalidate
     * after data changes so column widths repaint.
     */
    private void adjustTableHeight() {
        revalidate();
        repaint();
    }

    /**
     * Displays a dialog to add a new chain.
     */
    private void showAddChainDialog() {
        JTextField chainIdField = new JTextField();
        JTextField nameField = new JTextField();
        JTextField explorerField = new JTextField();
        JTextField apiKeyField = new JTextField();

        Object[] message = {
                "Chain ID (integer):", chainIdField,
                "Name:", nameField,
                "Explorer URL:", explorerField,
                "Explorer API Key (optional):", apiKeyField
        };

        int option = JOptionPane.showConfirmDialog(this, message, "Add New Chain", JOptionPane.OK_CANCEL_OPTION);
        if (option == JOptionPane.OK_OPTION) {
            try {
                int chainId = Integer.parseInt(chainIdField.getText().trim());
                String name = nameField.getText().trim();
                String explorer = explorerField.getText().trim();
                String apiKey = apiKeyField.getText().trim();

                if (name.isEmpty()) {
                    JOptionPane.showMessageDialog(this, "Name cannot be empty.", "Input Error", JOptionPane.ERROR_MESSAGE);
                    return;
                }

                if (config.getChain(chainId) != null) {
                    JOptionPane.showMessageDialog(this, "A chain with this Chain ID already exists.", "Duplicate Chain ID", JOptionPane.ERROR_MESSAGE);
                    return;
                }

                config.addOrUpdateChain(chainId, name, explorer, apiKey.isEmpty() ? "" : apiKey);

                loadData();
                tableModel.fireTableDataChanged();

                JOptionPane.showMessageDialog(this, "Chain added successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
                api.logging().logToOutput("Added new chain with ID " + chainId + ".");
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(this, "Chain ID must be an integer.", "Input Error", JOptionPane.ERROR_MESSAGE);
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(this, "An error occurred while adding the chain.", "Error", JOptionPane.ERROR_MESSAGE);
                api.logging().logToError("Error adding new chain: " + ex.getMessage());
            }
        }
    }

    private void editSelectedChain() {
        int selectedRow = table.getSelectedRow();
        if (selectedRow == -1) {
            JOptionPane.showMessageDialog(this, "Please select a chain to edit.", "No Selection", JOptionPane.WARNING_MESSAGE);
            return;
        }

        int modelRow = table.convertRowIndexToModel(selectedRow);
        ChainInfo chain = tableModel.getChainAt(modelRow);
        if (chain == null) {
            JOptionPane.showMessageDialog(this, "Selected chain does not exist.", "Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        JTextField nameField = new JTextField(chain.getName());
        JTextField explorerField = new JTextField(chain.getExplorer());
        Object[] message = {
                "Chain ID: " + chain.getChainId(),
                "Name:", nameField,
                "Explorer URL (optional):", explorerField
        };

        int option = JOptionPane.showConfirmDialog(this, message, "Edit Chain", JOptionPane.OK_CANCEL_OPTION);
        if (option != JOptionPane.OK_OPTION) {
            return;
        }

        String name = nameField.getText().trim();
        String explorer = explorerField.getText().trim();
        if (name.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Name cannot be empty.", "Input Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        config.updateChainDetails(chain.getChainId(), name, explorer);
        loadData();
        tableModel.fireTableDataChanged();
        JOptionPane.showMessageDialog(this, "Chain updated successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
    }

    /**
     * Removes the selected chain from the table and persistence.
     */
    private void removeSelectedChain() {
        int selectedRow = table.getSelectedRow();
        if (selectedRow == -1) {
            JOptionPane.showMessageDialog(this, "Please select a chain to remove.", "No Selection", JOptionPane.WARNING_MESSAGE);
            return;
        }

        int modelRow = table.convertRowIndexToModel(selectedRow);
        ChainInfo chain = tableModel.getChainAt(modelRow);

        if (chain == null) {
            JOptionPane.showMessageDialog(this, "Selected chain does not exist.", "Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        int confirm = JOptionPane.showConfirmDialog(this,
                "Are you sure you want to remove the chain: " + chain.getName() + " (ID: " + chain.getChainId() + ")?",
                "Confirm Removal",
                JOptionPane.YES_NO_OPTION);

        if (confirm == JOptionPane.YES_OPTION) {
            config.removeChain(chain.getChainId());

            loadData();
            tableModel.fireTableDataChanged();

            JOptionPane.showMessageDialog(this, "Chain removed successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
            api.logging().logToOutput("Removed chain with ID " + chain.getChainId() + ".");
        }
    }

    /**
     * Edits the API key for the selected chain.
     * This method is triggered by the "Edit API Key for Selected Chain" button.
     */
    private void editApiKeyForSelectedChain() {
        int selectedRow = table.getSelectedRow();
        if (selectedRow == -1) {
            JOptionPane.showMessageDialog(this, "Please select a chain to edit its API key.", "No Selection", JOptionPane.WARNING_MESSAGE);
            return;
        }

        int modelRow = table.convertRowIndexToModel(selectedRow);
        ChainInfo chain = tableModel.getChainAt(modelRow);

        if (chain == null) {
            JOptionPane.showMessageDialog(this, "Selected chain does not exist.", "Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        if (chain.getExplorer().isEmpty()) {
            JOptionPane.showMessageDialog(this, "This chain has no explorer configured (manual ABI mode). API key is not applicable.", "API Key Not Applicable", JOptionPane.INFORMATION_MESSAGE);
            return;
        }

        showEditApiKeyDialog(chain);
    }

    /**
     * Displays a dialog to edit the API key for a specific chain.
     *
     * @param chain The ChainInfo object to edit.
     */
    private void showEditApiKeyDialog(ChainInfo chain) {
        JPasswordField apiKeyField = new JPasswordField(chain.getExplorerAPIKey());

        Object[] message = {
                "Editing API Key for Chain: " + chain.getName() + " (ID: " + chain.getChainId() + ")",
                "Explorer API Key:", apiKeyField
        };

        int option = JOptionPane.showConfirmDialog(this, message, "Edit API Key", JOptionPane.OK_CANCEL_OPTION);
        if (option == JOptionPane.OK_OPTION) {
            String apiKey = new String(apiKeyField.getPassword()).trim();

            // Optionally, you can add validation for the API key format here

            config.updateExplorerAPIKey(chain.getChainId(), apiKey);

            loadData();
            tableModel.fireTableDataChanged();

            JOptionPane.showMessageDialog(this, "API Key updated successfully.", "Success", JOptionPane.INFORMATION_MESSAGE);
            api.logging().logToOutput("Updated API Key for chain ID " + chain.getChainId() + ".");
        }
    }

    private void persistSharedApiKeyFromField() {
        String typedKey = new String(sharedApiKeyField.getPassword()).trim();
        if (typedKey.equals(config.getSharedEtherscanApiKey())) {
            updateSharedKeyStatusLabel();
            return;
        }

        config.setSharedEtherscanApiKey(typedKey);
        updateSharedKeyStatusLabel();
        loadData();
        tableModel.fireTableDataChanged();
    }

    private void updateSharedKeyStatusLabel() {
        if (config.getSharedEtherscanApiKey().isEmpty()) {
            sharedApiKeyStatusLabel.setText("Not Set");
            sharedApiKeyStatusLabel.setForeground(new Color(255, 100, 100));
        } else {
            sharedApiKeyStatusLabel.setText("Set");
            sharedApiKeyStatusLabel.setForeground(new Color(0, 200, 0));
        }
    }

    /**
     * A custom TableModel for the chains table.
     * It handles the data representation and manipulation for the JTable.
     */
    private class ChainsTableModel extends AbstractTableModel {
        private String[] columnNames = {"Chain ID", "Name", "Explorer", "Mode", "API Key"};
        private List<ChainInfo> chains;

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
         * Sets the list of chains to be displayed in the table.
         *
         * @param chains A list of ChainInfo objects.
         */
        public void setChains(List<ChainInfo> chains) {
            this.chains = chains;
            fireTableDataChanged();
        }

        @Override
        public int getRowCount() {
            return chains == null ? 0 : chains.size();
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
            ChainInfo chain = chains.get(row);
            switch (col) {
                case 0:
                    return chain.getChainId();
                case 1:
                    return chain.getName();
                case 2:
                    return chain.getExplorer();
                case 3:
                    return chain.getExplorer().isEmpty() ? "Manual ABI only" : "Explorer enabled";
                case 4:
                    return apiKeyStatus(chain);
                default:
                    return null;
            }
        }

        @Override
        public boolean isCellEditable(int row, int col) {
            // All cells are non-editable except possibly future enhancements
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
         * Retrieves the ChainInfo object at the specified row.
         *
         * @param row The row index.
         * @return The corresponding ChainInfo object.
         */
        public ChainInfo getChainAt(int row) {
            if (chains == null || row < 0 || row >= chains.size()) {
                return null;
            }
            return chains.get(row);
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

    private String apiKeyStatus(ChainInfo chain) {
        if (chain.getExplorer().isEmpty()) {
            return "N/A";
        }
        if (config.isEtherscanFamilyExplorer(chain.getExplorer())) {
            String shared = config.getSharedEtherscanApiKey();
            String local = chain.getExplorerAPIKey();
            if (!shared.isEmpty()) {
                if (local.isEmpty() || local.equals(shared)) {
                    return "Set";
                }
                return "Overriden";
            }
            if (!local.isEmpty()) {
                return "Overriden";
            }
            return "Not Set";
        }
        if (!chain.getExplorerAPIKey().isEmpty()) {
            return "Set";
        }
        return "Not Set";
    }

    /**
     * A custom TableCellRenderer to render the API Key Status with enhanced visibility.
     * "Set" is displayed in green, "Overriden" in orange, "Not Set" in red and "N/A" in gray.
     * It preserves the table's default row background colors and borders to maintain dark theme compatibility.
     */
    private class ApiKeyStatusRenderer extends DefaultTableCellRenderer {

        public ApiKeyStatusRenderer() {
            setOpaque(true);
            setHorizontalAlignment(SwingConstants.CENTER);
            setFont(getFont().deriveFont(Font.BOLD));
        }

        @Override
        public Component getTableCellRendererComponent(JTable table, Object value,
                                                       boolean isSelected, boolean hasFocus, int row, int column) {
            super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
            String status = (String) value;
            if ("Set".equals(status)) {
                setText(status);
                setForeground(new Color(0, 200, 0)); // Bright Green for better visibility in dark theme
            } else if ("Overriden".equals(status)) {
                setText(status);
                setForeground(new Color(255, 180, 80));
            } else if ("N/A".equals(status)) {
                setText(status);
                setForeground(new Color(170, 170, 170));
            } else {
                setText(status);
                setForeground(new Color(255, 100, 100)); // Light Red for better visibility in dark theme
            }

            // Background is handled by the table's default renderer to maintain LAF compatibility
            return this;
        }
    }
}
