#!/usr/bin/env python3
# coding: utf-8

"""
@File   : ui_updater.py
@Author : sule01u
@Date   : 2024/10/10
@Desc   : UI文本更新工具
"""

from java.awt.event import ActionListener
from java.lang import Math
from localization.language_manager import get_text
from javax.swing import BorderFactory
from java.awt import Color

def update_main_ui(extender):
    """更新主界面文本"""
    extender._callbacks.setExtensionName(get_text("extension_name", "AutorizePro"))
    
    if hasattr(extender, "tabs"):
        extender.tabs.setTitleAt(0, get_text("tab_results", "Request/Response Viewers"))
        extender.tabs.setTitleAt(1, get_text("tab_configuration", "Configuration"))
        
        if hasattr(extender, "modified_requests_tabs"):
            extender.modified_requests_tabs.setTitleAt(0, get_text("table_modified", "Modified Request"))
            extender.modified_requests_tabs.setTitleAt(1, get_text("table_modified_response", "Modified Response"))
            extender.modified_requests_tabs.setTitleAt(2, get_text("expand", "Expand"))
            
        if hasattr(extender, "original_requests_tabs"):
            extender.original_requests_tabs.setTitleAt(0, get_text("table_originals", "Original Request"))
            extender.original_requests_tabs.setTitleAt(1, get_text("table_originals_response", "Original Response"))
            extender.original_requests_tabs.setTitleAt(2, get_text("expand", "Expand"))
            
        if hasattr(extender, "unauthenticated_requests_tabs"):
            extender.unauthenticated_requests_tabs.setTitleAt(0, get_text("table_unauthorized", "Unauthenticated Request"))
            extender.unauthenticated_requests_tabs.setTitleAt(1, get_text("table_unauthorized_response", "Unauthenticated Response"))
            extender.unauthenticated_requests_tabs.setTitleAt(2, get_text("expand", "Expand"))
    
    if hasattr(extender, "startButton"):
        if extender.startButton.isSelected():
            extender.startButton.setText(get_text("autorize_is_on", "AutorizePro is on"))
        else:
            extender.startButton.setText(get_text("autorize_is_off", "AutorizePro is off"))
    
    if hasattr(extender, "toggleLanguageButton"):
        extender.toggleLanguageButton.setText(get_text("language_toggle", "EN/中"))
    
    if hasattr(extender, "doUnauthorizedRequest"):
        extender.doUnauthorizedRequest.setText(get_text("check_unauthenticated", "Check unauthenticated"))
    
    if hasattr(extender, "interceptRequestsfromRepeater"):
        extender.interceptRequestsfromRepeater.setText(get_text("intercept_from_repeater", "Intercept requests from Repeater"))
    
    if hasattr(extender, "fetchCookiesHeaderButton"):
        extender.fetchCookiesHeaderButton.setText(get_text("fetch_cookie_button", "Fetch Cookies header"))
    
    if hasattr(extender, "fetchAuthorizationHeaderButton"):
        extender.fetchAuthorizationHeaderButton.setText(get_text("fetch_authorization_button", "Fetch Authorization header"))
    
    if hasattr(extender, "clearButton"):
        extender.clearButton.setText(get_text("clear_button", "Clear List"))
    
    if hasattr(extender, "autoScroll"):
        extender.autoScroll.setText(get_text("auto_scroll", "Auto Scroll"))
    
    if hasattr(extender, "ignore304"):
        extender.ignore304.setText(get_text("ignore_304", "Ignore 304/204 status code responses"))
        
    if hasattr(extender, "prevent304"):
        extender.prevent304.setText(get_text("prevent_304", "Prevent 304 Not Modified status code"))
        
    if hasattr(extender, "replaceQueryParam"):
        extender.replaceQueryParam.setText(get_text("replace_query_params", "Replace query params"))
        
    if hasattr(extender, "authHeadersLabel"):
        extender.authHeadersLabel.setText(get_text("auth_headers_label", "Authentication Headers:"))
        
    if hasattr(extender, "authHeadersField"):
        extender.authHeadersField.setToolTipText(get_text("auth_headers_tooltip", "Comma-separated list of authentication header names"))
        
    if hasattr(extender, "updateAuthHeadersButton"):
        extender.updateAuthHeadersButton.setText(get_text("update_auth_headers", "Update"))
    
    if hasattr(extender, "apiKeyEnabledCheckbox"):
        extender.apiKeyEnabledCheckbox.setText(get_text("enable_ai", "KEY"))
    
    if hasattr(extender, "exportPnl") and extender.exportPnl is not None:
        if hasattr(extender, "resultExportPanel"):
            border = BorderFactory.createTitledBorder(
                BorderFactory.createLineBorder(Color(120, 120, 120)), 
                get_text("export_results_section", "Export Test Results"))
            extender.resultExportPanel.setBorder(border)
            
        if hasattr(extender, "configPanel"):
            border = BorderFactory.createTitledBorder(
                BorderFactory.createLineBorder(Color(120, 120, 120)), 
                get_text("save_restore", "Save/Restore"))
            extender.configPanel.setBorder(border)
        
        if hasattr(extender, "exportButton"):
            extender.exportButton.setText(get_text("export_button", "Export"))
        
        if hasattr(extender, "removeDuplicates"):
            extender.removeDuplicates.setText(get_text("remove_duplicates", "Remove Duplicates"))
        
        if hasattr(extender, "saveStateButton"):
            extender.saveStateButton.setText(get_text("save_button", "Save Current Config"))
        
        if hasattr(extender, "restoreStateButton"):
            extender.restoreStateButton.setText(get_text("restore_button", "Import Saved Config"))
        
        if hasattr(extender, "exportLType"):
            extender.exportLType.setText(get_text("export_file_type", "File Type:"))
            
        if hasattr(extender, "exportLES"):
            extender.exportLES.setText(get_text("export_statuses", "Statuses:"))
        
        if hasattr(extender, "exportES"):
            currentSelection = extender.exportES.getSelectedItem()
            exportESItems = [
                get_text("all_statuses", "All Statuses"),
                get_text("as_table_filter", "As table filter"),
                get_text("status_bypassed", "Bypassed!"),
                get_text("status_is_enforced", "Is enforced???"),
                get_text("status_enforced", "Enforced!")
            ]
            extender.exportES.removeAllItems()
            for item in exportESItems:
                extender.exportES.addItem(item)
            
            try:
                extender.exportES.setSelectedItem(currentSelection)
            except:
                if extender.exportES.getItemCount() > 0:
                    extender.exportES.setSelectedIndex(0)
        
        extender.exportPnl.revalidate()
        extender.exportPnl.repaint()
    
    if hasattr(extender, "filtersTabs") and extender.filtersTabs is not None:
        extender.filtersTabs.setTitleAt(0, get_text("enforcement_detector", "Privilege Enforcement Rules"))
        extender.filtersTabs.setTitleAt(1, get_text("enforcement_detector_unauthorized", "Unauthorized Enforcement Rules"))
        extender.filtersTabs.setTitleAt(2, get_text("interception_filters", "Interception Filters"))
        extender.filtersTabs.setTitleAt(3, get_text("match_replace", "Match/Replace"))
        extender.filtersTabs.setTitleAt(4, get_text("table_filter", "Table Filter"))
        extender.filtersTabs.setTitleAt(5, get_text("save_restore", "Save/Restore"))
        
        if hasattr(extender, "filterLModified"):
            extender.filterLModified.setText(get_text("filter_modified", "Modified:"))
        if hasattr(extender, "filterLUnauthenticated"):
            extender.filterLUnauthenticated.setText(get_text("filter_unauthenticated", "Unauthenticated:"))
        if hasattr(extender, "filterLAIAnalyzed"):
            extender.filterLAIAnalyzed.setText(get_text("filter_ai_analyzed", "AI.Analyzed:"))
        if hasattr(extender, "showDisabledUnauthenticated"):
            extender.showDisabledUnauthenticated.setText(get_text("filter_disabled", "Disabled"))

def update_table_headers(extender):
    if hasattr(extender, "tableModel") and extender.tableModel is not None:
        # 对于AbstractTableModel，我们不能直接设置列名
        # 只能通知UI组件数据模型结构已变化，让它重新获取列名
        extender.tableModel.fireTableStructureChanged()
        
        if hasattr(extender, "logTable"):
            tableWidth = extender.logTable.getPreferredSize().width
            extender.logTable.getColumn("ID").setPreferredWidth(Math.round(tableWidth / 50 * 2))
            extender.logTable.getColumn(get_text("table_method", "Method")).setPreferredWidth(Math.round(tableWidth / 50 * 3))
            extender.logTable.getColumn(get_text("table_url", "URL")).setPreferredWidth(Math.round(tableWidth / 50 * 25))
            extender.logTable.getColumn(get_text("table_originals_len", "Orig. Len")).setPreferredWidth(Math.round(tableWidth / 50 * 4))
            extender.logTable.getColumn(get_text("table_modified_len", "Modif. Len")).setPreferredWidth(Math.round(tableWidth / 50 * 4))
            extender.logTable.getColumn(get_text("table_unauthorized_len", "Unauth. Len")).setPreferredWidth(Math.round(tableWidth / 50 * 4))
            extender.logTable.getColumn(get_text("table_status", "Authz. Status")).setPreferredWidth(Math.round(tableWidth / 50 * 4))
            extender.logTable.getColumn(get_text("table_unauthorized_status", "Unauth. Status")).setPreferredWidth(Math.round(tableWidth / 50 * 4))
            extender.logTable.getColumn(get_text("table_ai_analyzer", "AI. Analyzer")).setPreferredWidth(Math.round(tableWidth / 50 * 4))
            
            header = extender.logTable.getTableHeader()
            if header is not None:
                header.repaint() 