#!/usr/bin/env python3
# coding: utf-8

"""
@File   : table.py
@Author : sule01u
@Date   : 2024/10/10
@Desc   :
"""

from java.awt import Color
from java.lang import String
from java.lang import Integer
from java.lang import Runnable
from javax.swing import JTable
from javax.swing import JLabel
from javax.swing import JPanel
from javax.swing import RowFilter
from javax.swing import JCheckBox
from javax.swing import GroupLayout
from javax.swing import ListSelectionModel
from java.awt.event import MouseAdapter
from java.awt.event import ItemListener
from javax.swing.table import AbstractTableModel
from javax.swing.event import ListSelectionListener

from helpers.filters import expand, collapse
from localization.language_manager import get_text


class TableFilter():
    def __init__(self, extender):
        self._extender = extender

    def draw(self):
        """
        init show tab
        """

        filterLModified = JLabel(get_text("filter_modified", "Modified:"))
        filterLModified.setBounds(10, 10, 100, 30)
        self._extender.filterLModified = filterLModified

        filterLUnauthenticated = JLabel(get_text("filter_unauthenticated", "Unauthenticated:"))
        filterLUnauthenticated.setBounds(250, 10, 100, 30)
        self._extender.filterLUnauthenticated = filterLUnauthenticated

        filterLAIAnalyzed = JLabel(get_text("filter_ai_analyzed", "AI.Analyzed:"))
        filterLAIAnalyzed.setBounds(490, 10, 100, 30)
        self._extender.filterLAIAnalyzed = filterLAIAnalyzed

        # Existing Modified filters
        self._extender.showAuthBypassModified = JCheckBox(self._extender.BYPASSSED_STR)
        self._extender.showAuthBypassModified.setBounds(10, 35, 200, 30)
        self._extender.showAuthBypassModified.setSelected(True)
        self._extender.showAuthBypassModified.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthPotentiallyEnforcedModified = JCheckBox(self._extender.IS_ENFORCED_STR)
        self._extender.showAuthPotentiallyEnforcedModified.setBounds(10, 60, 200, 30)
        self._extender.showAuthPotentiallyEnforcedModified.setSelected(True)
        self._extender.showAuthPotentiallyEnforcedModified.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthEnforcedModified = JCheckBox(self._extender.ENFORCED_STR)
        self._extender.showAuthEnforcedModified.setBounds(10, 85, 200, 30)
        self._extender.showAuthEnforcedModified.setSelected(True)
        self._extender.showAuthEnforcedModified.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthBypassUnauthenticated = JCheckBox(self._extender.BYPASSSED_STR)
        self._extender.showAuthBypassUnauthenticated.setBounds(250, 35, 200, 30)
        self._extender.showAuthBypassUnauthenticated.setSelected(True)
        self._extender.showAuthBypassUnauthenticated.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthPotentiallyEnforcedUnauthenticated = JCheckBox(self._extender.IS_ENFORCED_STR)
        self._extender.showAuthPotentiallyEnforcedUnauthenticated.setBounds(250, 60, 200, 30)
        self._extender.showAuthPotentiallyEnforcedUnauthenticated.setSelected(True)
        self._extender.showAuthPotentiallyEnforcedUnauthenticated.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthEnforcedUnauthenticated = JCheckBox(self._extender.ENFORCED_STR)
        self._extender.showAuthEnforcedUnauthenticated.setBounds(250, 85, 200, 30)
        self._extender.showAuthEnforcedUnauthenticated.setSelected(True)
        self._extender.showAuthEnforcedUnauthenticated.addItemListener(TabTableFilter(self._extender))

        self._extender.showDisabledUnauthenticated = JCheckBox(get_text("filter_disabled", "Disabled"))
        self._extender.showDisabledUnauthenticated.setBounds(250, 110, 200, 30)
        self._extender.showDisabledUnauthenticated.setSelected(True)
        self._extender.showDisabledUnauthenticated.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthBypassAIAnalyzed = JCheckBox(self._extender.BYPASSSED_STR)
        self._extender.showAuthBypassAIAnalyzed.setBounds(490, 35, 200, 30)
        self._extender.showAuthBypassAIAnalyzed.setSelected(True)
        self._extender.showAuthBypassAIAnalyzed.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthPotentiallyEnforcedAIAnalyzed = JCheckBox(self._extender.IS_ENFORCED_STR)
        self._extender.showAuthPotentiallyEnforcedAIAnalyzed.setBounds(490, 60, 200, 30)
        self._extender.showAuthPotentiallyEnforcedAIAnalyzed.setSelected(True)
        self._extender.showAuthPotentiallyEnforcedAIAnalyzed.addItemListener(TabTableFilter(self._extender))

        self._extender.showAuthEnforcedAIAnalyzed = JCheckBox(self._extender.ENFORCED_STR)
        self._extender.showAuthEnforcedAIAnalyzed.setBounds(490, 85, 200, 30)
        self._extender.showAuthEnforcedAIAnalyzed.setSelected(True)
        self._extender.showAuthEnforcedAIAnalyzed.addItemListener(TabTableFilter(self._extender))

        self._extender.filterPnl = JPanel()
        layout = GroupLayout(self._extender.filterPnl)
        self._extender.filterPnl.setLayout(layout)
        layout.setAutoCreateGaps(True)
        layout.setAutoCreateContainerGaps(True)

        layout.setHorizontalGroup(layout.createSequentialGroup()
        .addGroup(layout.createParallelGroup()
        .addComponent(
            filterLModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthBypassModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthPotentiallyEnforcedModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthEnforcedModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        .addGroup(layout.createParallelGroup()
        .addComponent(
            filterLUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthBypassUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthPotentiallyEnforcedUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthEnforcedUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showDisabledUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        .addGroup(layout.createParallelGroup()
        .addComponent(
            filterLAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthBypassAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthPotentiallyEnforcedAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthEnforcedAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        )

        layout.setVerticalGroup(layout.createSequentialGroup()
        .addGroup(layout.createParallelGroup(GroupLayout.Alignment.BASELINE)
        .addComponent(
            filterLModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            filterLUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            filterLAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        .addGroup(layout.createParallelGroup(GroupLayout.Alignment.BASELINE)
        .addGroup(layout.createSequentialGroup()
        .addComponent(
            self._extender.showAuthBypassModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthPotentiallyEnforcedModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthEnforcedModified,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        .addGroup(layout.createSequentialGroup()
        .addComponent(
            self._extender.showAuthBypassUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthPotentiallyEnforcedUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthEnforcedUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showDisabledUnauthenticated,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        .addGroup(layout.createSequentialGroup()
        .addComponent(
            self._extender.showAuthBypassAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthPotentiallyEnforcedAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        .addComponent(
            self._extender.showAuthEnforcedAIAnalyzed,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
            GroupLayout.PREFERRED_SIZE,
        )
        )
        )
        )


class TabTableFilter(ItemListener):
    def __init__(self, extender):
        self._extender = extender

    def itemStateChanged(self, e):
        self._extender.tableSorter.sort()


class TableModel(AbstractTableModel):
    def __init__(self, extender):
        self._extender = extender

    def removeRows(self, rows):
        rows.sort(reverse=True)
        for row in rows:
            self._extender._log.pop(row)
        self.fireTableDataChanged()

    def getRowCount(self):
        try:
            return self._extender._log.size()
        except:
            return 0

    def getColumnCount(self):
        return 9

    def getColumnName(self, columnIndex):
        data = [
            'ID', 
            get_text("table_method", "Method"), 
            get_text("table_url", "URL"), 
            get_text("table_originals_len", "Orig. Len"), 
            get_text("table_modified_len", "Modif. Len"), 
            get_text("table_unauthorized_len", "Unauth. Len"), 
            get_text("table_status", "Authz. Status"), 
            get_text("table_unauthorized_status", "Unauth. Status"),
            get_text("table_ai_analyzer", "AI. Analyzer")
        ]
        try:
            return data[columnIndex]
        except IndexError:
            return ""

    def getColumnClass(self, columnIndex):
        data = [Integer, String, String, Integer, Integer, Integer, String, String, String]  # 分析结果为string类型
        try:
            return data[columnIndex]
        except IndexError:
            return ""

    def getValueAt(self, rowIndex, columnIndex):
        logEntry = self._extender._log.get(rowIndex)
        if columnIndex == 0:
            return logEntry._id
        if columnIndex == 1:
            return logEntry._method
        if columnIndex == 2:
            return logEntry._url.toString()
        if columnIndex == 3:
            response = logEntry._originalrequestResponse.getResponse()
            return len(logEntry._originalrequestResponse.getResponse()) - self._extender._helpers.analyzeResponse(
                response).getBodyOffset()
        if columnIndex == 4:
            response = logEntry._requestResponse.getResponse()
            return len(logEntry._requestResponse.getResponse()) - self._extender._helpers.analyzeResponse(
                response).getBodyOffset()
        if columnIndex == 5:
            if logEntry._unauthorizedRequestResponse is not None:
                response = logEntry._unauthorizedRequestResponse.getResponse()
                return len(
                    logEntry._unauthorizedRequestResponse.getResponse()) - self._extender._helpers.analyzeResponse(
                    response).getBodyOffset()
            else:
                return 0
        if columnIndex == 6:
            return logEntry._enfocementStatus
        if columnIndex == 7:
            return logEntry._enfocementStatusUnauthorized
        if columnIndex == 8:
            return logEntry._aiAnalysisResult
        return ""


class TableSelectionListener(ListSelectionListener):
    """Class Responsible for the multi-row deletion"""

    def __init__(self, extender):
        self._extender = extender

    def valueChanged(self, e):
        rows = [i for i in self._table.getSelectedRows()]
        self._extender.tableModel.removeRows(rows)


class Table(JTable):
    def __init__(self, extender):
        self._extender = extender
        self._extender.tableModel = TableModel(extender)
        self.setModel(self._extender.tableModel)
        self.addMouseListener(Mouseclick(self._extender))
        self.getColumnModel().getColumn(0).setPreferredWidth(450)
        self.setRowSelectionAllowed(True)
        # Enables multi-row selection
        self.setSelectionMode(ListSelectionModel.MULTIPLE_INTERVAL_SELECTION)

    def prepareRenderer(self, renderer, row, col):
        comp = JTable.prepareRenderer(self, renderer, row, col)
        value = self._extender.tableModel.getValueAt(self._extender.logTable.convertRowIndexToModel(row), col)
        # 列索引 6 是 "Authz. Status"
        # 列索引 7 是 "Unauth. Status"
        # 列索引 8 是 "AI. Analyzer"
        if col == 6 or col == 7 or col == 8:
            if value == self._extender.BYPASSSED_STR:
                comp.setBackground(Color(255, 153, 153))
                comp.setForeground(Color.BLACK)
            elif value == self._extender.IS_ENFORCED_STR:
                comp.setBackground(Color(255, 204, 153))
                comp.setForeground(Color.BLACK)
            elif value == self._extender.ENFORCED_STR:
                comp.setBackground(Color(204, 255, 153))
                comp.setForeground(Color.BLACK)
        else:
            comp.setForeground(Color.BLACK)
            comp.setBackground(Color.WHITE)

        selectedRows = self._extender.logTable.getSelectedRows()
        if row in selectedRows:
            comp.setBackground(Color(201, 215, 255))
            comp.setForeground(Color.BLACK)

        return comp

    def changeSelection(self, row, col, toggle, extend):
        # show the log entry for the selected row
        logEntry = self._extender._log.get(self._extender.logTable.convertRowIndexToModel(row))
        self._extender._requestViewer.setMessage(logEntry._requestResponse.getRequest(), True)
        self._extender._responseViewer.setMessage(logEntry._requestResponse.getResponse(), False)
        self._extender._originalrequestViewer.setMessage(logEntry._originalrequestResponse.getRequest(), True)
        self._extender._originalresponseViewer.setMessage(logEntry._originalrequestResponse.getResponse(), False)

        if logEntry._unauthorizedRequestResponse is not None:
            self._extender._unauthorizedrequestViewer.setMessage(logEntry._unauthorizedRequestResponse.getRequest(),
                                                                 True)
            self._extender._unauthorizedresponseViewer.setMessage(logEntry._unauthorizedRequestResponse.getResponse(),
                                                                  False)
        else:
            self._extender._unauthorizedrequestViewer.setMessage("Request disabled", True)
            self._extender._unauthorizedresponseViewer.setMessage("Response disabled", False)

        self._extender._currentlyDisplayedItem = logEntry

        # 使用固定的列索引而不是根据列名判断
        if col == 3:  # Orig. Len
            collapse(self._extender, self._extender.modified_requests_tabs)
            collapse(self._extender, self._extender.unauthenticated_requests_tabs)
            expand(self._extender, self._extender.original_requests_tabs)
        elif col == 4:  # Modif. Len
            collapse(self._extender, self._extender.original_requests_tabs)
            collapse(self._extender, self._extender.unauthenticated_requests_tabs)
            # 展开并显示Modified Response选项卡
            self._extender.modified_requests_tabs.setSelectedIndex(1)  # 选择响应选项卡
            expand(self._extender, self._extender.modified_requests_tabs)
        elif col == 6:  # Authz. Status
            collapse(self._extender, self._extender.original_requests_tabs)
            collapse(self._extender, self._extender.unauthenticated_requests_tabs)
            # 展开并显示Modified Request选项卡
            self._extender.modified_requests_tabs.setSelectedIndex(0)  # 选择请求选项卡
            expand(self._extender, self._extender.modified_requests_tabs)
        elif col == 5 or col == 7:  # Unauth. Len or Unauth. Status
            collapse(self._extender, self._extender.original_requests_tabs)
            collapse(self._extender, self._extender.modified_requests_tabs)
            expand(self._extender, self._extender.unauthenticated_requests_tabs)
        elif col == 8:  # AI. Analyzer
            collapse(self._extender, self._extender.original_requests_tabs)
            collapse(self._extender, self._extender.unauthenticated_requests_tabs)
            expand(self._extender, self._extender.modified_requests_tabs)
        else:
            collapse(self._extender, self._extender.original_requests_tabs)
            collapse(self._extender, self._extender.modified_requests_tabs)
            collapse(self._extender, self._extender.unauthenticated_requests_tabs)

        JTable.changeSelection(self, row, col, toggle, extend)
        return


class LogEntry:
    def __init__(self, id, requestResponse, method, url, originalrequestResponse, enforcementStatus,
                 unauthorizedRequestResponse, enforcementStatusUnauthorized, aiAnalysisResult=""):
        self._id = id
        self._requestResponse = requestResponse
        self._originalrequestResponse = originalrequestResponse
        self._method = method
        self._url = url
        self._enfocementStatus = enforcementStatus
        self._unauthorizedRequestResponse = unauthorizedRequestResponse
        self._enfocementStatusUnauthorized = enforcementStatusUnauthorized
        self._aiAnalysisResult = aiAnalysisResult
        return


class Mouseclick(MouseAdapter):
    def __init__(self, extender):
        self._extender = extender

    def mouseReleased(self, evt):
        if evt.button == 3:
            self._extender.menu.show(evt.getComponent(), evt.getX(), evt.getY())


class TableRowFilter(RowFilter):
    def __init__(self, extender):
        self._extender = extender

    def include(self, entry):
        # 列索引 6 是 "Authz. Status"
        # 列索引 7 是 "Unauth. Status"
        # 列索引 8 是 "AI. Analyzer"
        
        if self._extender.showAuthBypassModified.isSelected() and self._extender.BYPASSSED_STR == entry.getValue(6):
            return True
        elif self._extender.showAuthPotentiallyEnforcedModified.isSelected() and self._extender.IS_ENFORCED_STR == entry.getValue(6):
            return True
        elif self._extender.showAuthEnforcedModified.isSelected() and self._extender.ENFORCED_STR == entry.getValue(6):
            return True
        elif self._extender.showAuthBypassUnauthenticated.isSelected() and self._extender.BYPASSSED_STR == entry.getValue(7):
            return True
        elif self._extender.showAuthPotentiallyEnforcedUnauthenticated.isSelected() and self._extender.IS_ENFORCED_STR == entry.getValue(7):
            return True
        elif self._extender.showAuthEnforcedUnauthenticated.isSelected() and self._extender.ENFORCED_STR == entry.getValue(7):
            return True
        elif self._extender.showDisabledUnauthenticated.isSelected() and "Disabled" == entry.getValue(7):
            return True
        elif self._extender.showAuthBypassAIAnalyzed.isSelected() and self._extender.BYPASSSED_STR == entry.getValue(8):
            return True
        elif self._extender.showAuthPotentiallyEnforcedAIAnalyzed.isSelected() and self._extender.IS_ENFORCED_STR == entry.getValue(8):
            return True
        elif self._extender.showAuthEnforcedAIAnalyzed.isSelected() and self._extender.ENFORCED_STR == entry.getValue(8):
            return True
        
        return False


class UpdateTableEDT(Runnable):
    def __init__(self, extender, action, firstRow, lastRow, column=None):
        self._extender = extender
        self._action = action
        self._firstRow = firstRow
        self._lastRow = lastRow
        self._column = column

    def run(self):
        if self._action == "insert":
            try:
                self._extender.tableModel.fireTableRowsInserted(self._firstRow, self._lastRow)
            except:
                pass
        elif self._action == "update":
            try:
                self._extender.tableModel.fireTableRowsUpdated(self._firstRow, self._lastRow)
                # 如果有AI分析结果，确保触发表格重绘
                if hasattr(self._extender, 'logTable') and self._extender.logTable is not None:
                    try:
                        self._extender.logTable.repaint()
                    except:
                        pass
            except:
                pass
        elif self._action == "delete":
            try:
                self._extender.tableModel.fireTableRowsDeleted(self._firstRow, self._lastRow)
            except:
                pass
        elif self._action == "cell":
            try:
                if self._column is not None:
                    self._extender.tableModel.fireTableCellUpdated(self._firstRow, self._column)
            except:
                pass

