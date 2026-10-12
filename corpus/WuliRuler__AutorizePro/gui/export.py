#!/usr/bin/env python3
# coding: utf-8

"""
@File   : export.py
@Author : sule01u
@Date   : 2024/10/10
@Desc   : 导出报告
"""

import sys
sys.path.append("..")

from localization.language_manager import get_text, get_language_manager

from java.io import File
from java.awt import Font
from javax.swing import JLabel
from javax.swing import JPanel
from javax.swing import JFrame
from javax.swing import JButton
from javax.swing import JCheckBox
from javax.swing import JComboBox
from javax.swing import GroupLayout
from javax.swing import JFileChooser
from javax.swing import JSeparator, BorderFactory
from javax.swing import JOptionPane
from java.awt import Color
from java.awt.event import ItemListener

from save_restore import SaveRestore


class RemoveDups(ItemListener):
    def __init__(self, extender):
        self._extender = extender

    def itemStateChanged(self, e):
        return True


class Export():
    def __init__(self, extender):
        self._extender = extender
        self.BYPASSSED_STR = extender.BYPASSSED_STR
        self.ENFORCED_STR = extender.ENFORCED_STR
        self.IS_ENFORCED_STR = extender.IS_ENFORCED_STR
        self._log = extender._log
        self.save_restore = SaveRestore(extender)

    def draw(self):
        """ init Save/Restore
        """

        # 导出结果区域 - 标题和边框
        resultExportPanel = JPanel()
        resultExportPanel.setBorder(BorderFactory.createTitledBorder(
            BorderFactory.createLineBorder(Color(120, 120, 120)), 
            get_text("export_results_section", "Export Test Results")))
        # 保存面板引用以便更新边框
        self._extender.resultExportPanel = resultExportPanel

        exportLType = JLabel(get_text("export_file_type", "File Type:"))
        exportLType.setBounds(10, 50, 100, 30)
        self._extender.exportLType = exportLType

        exportFileTypes = ["HTML", "CSV"]
        self.exportType = JComboBox(exportFileTypes)
        self.exportType.setBounds(100, 50, 200, 30)
        self._extender.exportType = self.exportType

        # 使用国际化字符串
        exportESItems = [
            get_text("all_statuses", "All Statuses"),
            get_text("as_table_filter", "As table filter"),
            get_text("status_bypassed", self.BYPASSSED_STR),
            get_text("status_is_enforced", self.IS_ENFORCED_STR),
            get_text("status_enforced", self.ENFORCED_STR)
        ]
        self.exportES = JComboBox(exportESItems)
        self.exportES.setBounds(100, 90, 200, 30)
        self._extender.exportES = self.exportES

        exportLES = JLabel(get_text("export_statuses", "Statuses:"))
        exportLES.setBounds(10, 90, 100, 30)
        self._extender.exportLES = exportLES

        self.removeDuplicates = JCheckBox(get_text("remove_duplicates", "Remove Duplicates"))
        self.removeDuplicates.setBounds(8, 120, 300, 30)
        self.removeDuplicates.setSelected(True)
        self.removeDuplicates.addItemListener(RemoveDups(self._extender))
        self._extender.removeDuplicates = self.removeDuplicates

        self.exportButton = JButton(get_text("export_button", "Export"),
                                    actionPerformed=self.export)
        self.exportButton.setBounds(390, 50, 100, 30)
        self._extender.exportButton = self.exportButton

        # 配置管理区域 - 标题和边框
        configPanel = JPanel()
        configPanel.setBorder(BorderFactory.createTitledBorder(
            BorderFactory.createLineBorder(Color(120, 120, 120)), 
            get_text("config_section", "Configuration Management")))
        # 保存面板引用以便更新边框
        self._extender.configPanel = configPanel

        self.saveStateButton = JButton(get_text("save_button", "Save Current Config"),
                                    actionPerformed=self.saveStateAction)
        self.saveStateButton.setBounds(10, 200, 180, 30)
        self._extender.saveStateButton = self.saveStateButton

        self.restoreStateButton = JButton(get_text("restore_button", "Import Saved Config"),
                                        actionPerformed=self.restoreStateAction)
        self.restoreStateButton.setBounds(390, 200, 180, 30)
        self._extender.restoreStateButton = self.restoreStateButton

        # 创建面板和布局
        self._extender.exportPnl = JPanel()
        layout = GroupLayout(self._extender.exportPnl)
        self._extender.exportPnl.setLayout(layout)
        layout.setAutoCreateGaps(True)
        layout.setAutoCreateContainerGaps(True)

        # 设置水平布局
        layout.setHorizontalGroup(layout.createParallelGroup()
            # 导出结果区域
            .addComponent(
                resultExportPanel,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
            # 配置管理区域
            .addComponent(
                configPanel,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
        )

        # 导出结果区域内部布局
        resultLayout = GroupLayout(resultExportPanel)
        resultExportPanel.setLayout(resultLayout)
        resultLayout.setAutoCreateGaps(True)
        resultLayout.setAutoCreateContainerGaps(True)
        
        resultLayout.setHorizontalGroup(resultLayout.createSequentialGroup()
            .addGroup(resultLayout.createParallelGroup()
                .addComponent(
                    exportLType,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
                .addComponent(
                    exportLES,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
                .addComponent(
                    self.removeDuplicates,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
            )
            .addGroup(resultLayout.createParallelGroup()
                .addComponent(
                    self.exportType,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
                .addComponent(
                    self.exportES,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
            )
            .addGroup(resultLayout.createParallelGroup()
                .addComponent(
                    self.exportButton,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
            )
        )

        resultLayout.setVerticalGroup(resultLayout.createSequentialGroup()
            .addGroup(resultLayout.createParallelGroup(GroupLayout.Alignment.BASELINE)
                .addComponent(
                    exportLType,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
                .addComponent(
                    self.exportType,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
                .addComponent(
                    self.exportButton,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
            )
            .addGroup(resultLayout.createParallelGroup(GroupLayout.Alignment.BASELINE)
                .addComponent(
                    exportLES,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
                .addComponent(
                    self.exportES,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
            )
            .addGroup(resultLayout.createSequentialGroup()
                .addComponent(
                    self.removeDuplicates,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                    GroupLayout.PREFERRED_SIZE,
                )
            )
        )

        # 配置管理区域内部布局
        configLayout = GroupLayout(configPanel)
        configPanel.setLayout(configLayout)
        configLayout.setAutoCreateGaps(True)
        configLayout.setAutoCreateContainerGaps(True)
        
        configLayout.setHorizontalGroup(configLayout.createSequentialGroup()
            .addComponent(
                self.saveStateButton,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
            .addComponent(
                self.restoreStateButton,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
        )

        configLayout.setVerticalGroup(configLayout.createParallelGroup(GroupLayout.Alignment.CENTER)
            .addComponent(
                self.saveStateButton,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
            .addComponent(
                self.restoreStateButton,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
        )

        layout.setVerticalGroup(layout.createSequentialGroup()
            .addComponent(
                resultExportPanel,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
            .addGap(20)  # 添加20像素的垂直间距
            .addComponent(
                configPanel,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
                GroupLayout.PREFERRED_SIZE,
            )
        )

    def export(self, event):
        from localization.language_manager import get_text
        html_type = "HTML"  # HTML文件类型名称保持不变
        csv_type = "CSV"    # CSV文件类型名称保持不变
            
        file_type = self.exportType.getSelectedItem()
        
        if file_type == html_type:
            self.exportToHTML()
        else:
            self.exportToCSV()

    def saveStateAction(self, event):
        self.save_restore.saveState()

    def restoreStateAction(self, event):
        self.save_restore.restoreState()

    def exportToHTML(self):
        from localization.language_manager import get_text, get_language_manager
        
        try:
            parentFrame = JFrame()
            fileChooser = JFileChooser()
            fileChooser.setSelectedFile(File("AutorizeProReport.html"))
            fileChooser.setDialogTitle("Save AutorizePro Report")
            userSelection = fileChooser.showSaveDialog(parentFrame)
            if userSelection == JFileChooser.APPROVE_OPTION:
                fileToSave = fileChooser.getSelectedFile()
            else:
                return

            enforcementStatusFilter = self.exportES.getSelectedItem()
            
            # 获取本地化的状态字符串用于比较
            all_statuses = get_text("all_statuses", "All Statuses")
            as_table_filter = get_text("as_table_filter", "As table filter")
            disabled_str = get_text("filter_disabled", "Disabled")
            
            # 检查日志是否为空
            if self._log.size() == 0:
                return
            
            htmlContent = """<html><title>Report from AutorizePro</title>
            <style>
            .datagrid table { border-collapse: collapse; text-align: left; width: 100%; }
                .datagrid {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #006699; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; }
                .datagrid table td, .datagrid table th { padding: 3px 10px; }
                .datagrid table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #006699), color-stop(1, #00557F) );background:-moz-linear-gradient( center top, #006699 5%, #00557F 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#006699', endColorstr='#00557F');background-color:#006699; color:#FFFFFF; font-size: 15px; font-weight: bold; border-left: 1px solid #0070A8; } .datagrid table thead th:first-child { border: none; }.datagrid table tbody td { color: #00496B; border-left: 1px solid #E1EEF4;font-size: 12px;font-weight: normal; }.datagrid table tbody .alt td { background: #E1EEF4; color: #00496B; }.datagrid table tbody td:first-child { border-left: none; }.datagrid table tbody tr:last-child td { border-bottom: none; }.datagrid table tfoot td div { border-top: 1px solid #006699;background: #E1EEF4;} .datagrid table tfoot td { padding: 0; font-size: 12px } .datagrid table tfoot td div{ padding: 2px; }.datagrid table tfoot td ul { margin: 0; padding:0; list-style: none; text-align: right; }.datagrid table tfoot  li { display: inline; }.datagrid table tfoot li a { text-decoration: none; display: inline-block;  padding: 2px 8px; margin: 1px;color: #FFFFFF;border: 1px solid #006699;-webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #006699), color-stop(1, #00557F) );background:-moz-linear-gradient( center top, #006699 5%, #00557F 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#006699', endColorstr='#00557F');background-color:#006699; }.datagrid table tfoot ul.active, .datagrid table tfoot ul a:hover { text-decoration: none;border-color: #006699; color: #FFFFFF; background: none; background-color:#00557F;}div.dhtmlx_window_active, div.dhx_modal_cover_dv { position: fixed !important; }
            table {
            width: 100%;
            table-layout: fixed;
            }
            td {
                border: 1px solid #35f;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            td.a {
                width: 13%;
                white-space: nowrap;
            }
            td.b {
                width: 9%;
                word-wrap: break-word;
            }
            </style>
            <body>
            <h1>AutorizePro Report<h1>
            <div class="datagrid"><table>
            <thead><tr><th width=\"3%\">ID</th><th width=\"5%\">Method</th><th width=\"43%\">URL</th><th width=\"9%\">Original length</th><th width=\"9%\">Modified length</th><th width=\"9%\">Unauthorized length</th><th width=\"11%\">Authorization Enforcement Status</th><th width=\"11%\">Authorization Unauthenticated Status</th><th width=\"11%\">AI Analysis Result</th></tr></thead>
            <tbody>"""
            unique_HTML_lines = set()  # 用于存储唯一值
            entries_count = 0  # 计数器，用于统计符合条件的条目数量
            try:
                for i in range(0,self._log.size()):
                    if self.removeDuplicates.isSelected():
                        lineData = "\t%s\t%s\t%s\t%s\n" % (self._log.get(i)._method, self._log.get(i)._url, self._log.get(i)._enfocementStatus,self._log.get(i)._enfocementStatusUnauthorized)
                        if lineData in unique_HTML_lines:
                            continue
                        else:
                            unique_HTML_lines.add(lineData)
                    color_modified = ""
                    if self._log.get(i)._enfocementStatus == self.BYPASSSED_STR:
                        color_modified = "red"
                    elif self._log.get(i)._enfocementStatus == self.IS_ENFORCED_STR:
                        color_modified = "yellow"
                    elif self._log.get(i)._enfocementStatus == self.ENFORCED_STR:
                        color_modified = "LawnGreen"

                    color_unauthorized = ""
                    if self._log.get(i)._enfocementStatusUnauthorized == self.BYPASSSED_STR:
                        color_unauthorized = "red"
                    elif self._log.get(i)._enfocementStatusUnauthorized == self.IS_ENFORCED_STR:
                        color_unauthorized = "yellow"
                    elif self._log.get(i)._enfocementStatusUnauthorized == self.ENFORCED_STR:
                        color_unauthorized = "LawnGreen"
                    
                    # 简化过滤条件检查逻辑，避免复杂的字符串比较
                    should_add = False
                    
                    # 第一种情况："所有状态" - 无论选择什么语言，都检查状态的第一个选项
                    if self.exportES.getSelectedIndex() == 0:
                        should_add = True
                        
                    # 第二种情况："表格过滤器" - 选项索引为1
                    elif self.exportES.getSelectedIndex() == 1:
                        if ((self._extender.showAuthBypassModified.isSelected() and self.BYPASSSED_STR == self._log.get(i)._enfocementStatus) or
                            (self._extender.showAuthPotentiallyEnforcedModified.isSelected() and self.IS_ENFORCED_STR == self._log.get(i)._enfocementStatus) or
                            (self._extender.showAuthEnforcedModified.isSelected() and self.ENFORCED_STR == self._log.get(i)._enfocementStatus) or
                            (self._extender.showAuthBypassUnauthenticated.isSelected() and self.BYPASSSED_STR == self._log.get(i)._enfocementStatusUnauthorized) or
                            (self._extender.showAuthPotentiallyEnforcedUnauthenticated.isSelected() and self.IS_ENFORCED_STR == self._log.get(i)._enfocementStatusUnauthorized) or
                            (self._extender.showAuthEnforcedUnauthenticated.isSelected() and self.ENFORCED_STR == self._log.get(i)._enfocementStatusUnauthorized) or
                            (self._extender.showDisabledUnauthenticated.isSelected() and disabled_str == self._log.get(i)._enfocementStatusUnauthorized)):
                            should_add = True
                    
                    # 第三种情况：特定状态选择
                    else:
                        if (enforcementStatusFilter == self._log.get(i)._enfocementStatus) or (enforcementStatusFilter == self._log.get(i)._enfocementStatusUnauthorized):
                            should_add = True
                    
                    if should_add:
                        try:
                            ai_color = ""
                            ai_result = self._log.get(i)._aiAnalysisResult
                            if ai_result == self.BYPASSSED_STR:
                                ai_color = "red"
                            elif ai_result == self.IS_ENFORCED_STR:
                                ai_color = "yellow"
                            elif ai_result == self.ENFORCED_STR:
                                ai_color = "LawnGreen"
                            htmlContent += "<tr><td>%d</td><td>%s</td><td><a href=\"%s\">%s</a></td><td>%d</td><td>%d</td><td>%d</td><td bgcolor=\"%s\">%s</td><td bgcolor=\"%s\">%s</td><td bgcolor=\"%s\">%s</td></tr>" % (
                                self._log.get(i)._id, 
                                self._log.get(i)._method, 
                                self._log.get(i)._url, 
                                self._log.get(i)._url, 
                                len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, 
                                len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, 
                                len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, 
                                color_modified, 
                                self._log.get(i)._enfocementStatus, 
                                color_unauthorized, 
                                self._log.get(i)._enfocementStatusUnauthorized,
                                ai_color,
                                ai_result
                            )
                            entries_count += 1
                        except:
                            pass
                            
            except:
                pass

            htmlContent += "</tbody></table></div></body></html>"
            
            if entries_count == 0:
                return
                
            try:
                f = open(fileToSave.getAbsolutePath(), 'w')
                f.writelines(htmlContent)
                f.close()
            except:
                pass
        except:
            pass

    def exportToCSV(self):
        from localization.language_manager import get_text, get_language_manager
        
        try:
            parentFrame = JFrame()
            fileChooser = JFileChooser()
            fileChooser.setSelectedFile(File("AutorizeProReport.csv"))
            fileChooser.setDialogTitle("Save AutorizePro Report")
            userSelection = fileChooser.showSaveDialog(parentFrame)
            if userSelection == JFileChooser.APPROVE_OPTION:
                fileToSave = fileChooser.getSelectedFile()
            else:
                return

            enforcementStatusFilter = self.exportES.getSelectedItem()
            
            all_statuses = get_text("all_statuses", "All Statuses")
            as_table_filter = get_text("as_table_filter", "As table filter")
            disabled_str = get_text("filter_disabled", "Disabled")
            
            if self._log.size() == 0:
                return
                
            csvContent = "id\tMethod\tURL\tOriginal length\tModified length\tUnauthorized length\tAuthorization Enforcement Status\tAuthorization Unauthenticated Status\tAI Analysis Result\n"

            unique_CVS_lines = set()
            entries_count = 0
            try:
                for i in range(0, self._log.size()):
                    if self.removeDuplicates.isSelected():
                        lineData = "\t%s\t%s\t%s\t%s\n" % (self._log.get(i)._method, self._log.get(i)._url, self._log.get(i)._enfocementStatus,self._log.get(i)._enfocementStatusUnauthorized)
                        if lineData in unique_CVS_lines:
                            continue
                        else:
                            unique_CVS_lines.add(lineData)
                    
                    should_add = False
                    
                    if self.exportES.getSelectedIndex() == 0:
                        should_add = True
                        
                    elif self.exportES.getSelectedIndex() == 1:
                        if ((self._extender.showAuthBypassModified.isSelected() and self.BYPASSSED_STR == self._log.get(i)._enfocementStatus) or
                            (self._extender.showAuthPotentiallyEnforcedModified.isSelected() and self.IS_ENFORCED_STR == self._log.get(i)._enfocementStatus) or
                            (self._extender.showAuthEnforcedModified.isSelected() and self.ENFORCED_STR == self._log.get(i)._enfocementStatus) or
                            (self._extender.showAuthBypassUnauthenticated.isSelected() and self.BYPASSSED_STR == self._log.get(i)._enfocementStatusUnauthorized) or
                            (self._extender.showAuthPotentiallyEnforcedUnauthenticated.isSelected() and self.IS_ENFORCED_STR == self._log.get(i)._enfocementStatusUnauthorized) or
                            (self._extender.showAuthEnforcedUnauthenticated.isSelected() and self.ENFORCED_STR == self._log.get(i)._enfocementStatusUnauthorized) or
                            (self._extender.showDisabledUnauthenticated.isSelected() and disabled_str == self._log.get(i)._enfocementStatusUnauthorized)):
                            should_add = True
                    
                    else:
                        if (enforcementStatusFilter == self._log.get(i)._enfocementStatus) or (enforcementStatusFilter == self._log.get(i)._enfocementStatusUnauthorized):
                            should_add = True
                    
                    if should_add:
                        try:
                            csvContent += "%d\t%s\t%s\t%d\t%d\t%d\t%s\t%s\t%s\n" % (
                                self._log.get(i)._id, 
                                self._log.get(i)._method, 
                                self._log.get(i)._url, 
                                len(self._log.get(i)._originalrequestResponse.getResponse()) if self._log.get(i)._originalrequestResponse is not None else 0, 
                                len(self._log.get(i)._requestResponse.getResponse()) if self._log.get(i)._requestResponse is not None else 0, 
                                len(self._log.get(i)._unauthorizedRequestResponse.getResponse()) if self._log.get(i)._unauthorizedRequestResponse is not None else 0, 
                                self._log.get(i)._enfocementStatus, 
                                self._log.get(i)._enfocementStatusUnauthorized,
                                self._log.get(i)._aiAnalysisResult
                            )
                            entries_count += 1
                        except:
                            pass
            except:
                pass

            if entries_count == 0:
                return
                
            try:
                f = open(fileToSave.getAbsolutePath(), 'w')
                f.writelines(csvContent)
                f.close()
            except:
                pass
        except:
            pass

