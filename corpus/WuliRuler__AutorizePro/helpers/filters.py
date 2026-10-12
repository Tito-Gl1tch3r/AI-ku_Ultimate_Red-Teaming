#!/usr/bin/env python3
# coding: utf-8

"""
@File   : filters.py
@Author : sule01u
@Date   : 2024/10/10
@Desc   : 帮助处理 Burp Suite 拦截过滤器的辅助函数，包括过滤器添加、删除、修改，以及代理消息的处理。
"""

from java.awt import GridLayout
from burp import IInterceptedProxyMessage
from localization.language_manager import get_text


def addFilterHelper(typeObj, model, textObj):
    typeName = typeObj.getSelectedItem().split(":")[0]
    model.addElement(typeName + ": " + textObj.getText().strip())
    textObj.setText("")


def delFilterHelper(listObj):
    index = listObj.getSelectedIndex()
    if not index == -1:
        listObj.getModel().remove(index)


def modFilterHelper(listObj, typeObj, textObj):
    index = listObj.getSelectedIndex()
    if not index == -1:
        valt = listObj.getSelectedValue()
        val = valt.split(":", 1)[1].strip()
        modifiedFilter = valt.split(":", 1)[0].strip() + ":"
        typeObj.getModel().setSelectedItem(modifiedFilter)
        if ("Scope items" not in valt) and ("Content-Len" not in valt):
            textObj.setText(val)
        listObj.getModel().remove(index)


def expand(extender, comp):
    # 设置默认选中的Tab，这里确保总是先显示请求Tab
    comp.setSelectedIndex(0)  
    
    # 使用翻译功能设置标签文本
    comp.setTitleAt(2, get_text("collapse", "Collapse"))

    # 移除所有Tab页面
    extender.requests_panel.remove(extender.modified_requests_tabs)
    extender.requests_panel.remove(extender.original_requests_tabs)
    extender.requests_panel.remove(extender.unauthenticated_requests_tabs)

    # 只添加选中的Tab组
    extender.requests_panel.add(comp)
    # 确保使用单个组件的布局
    extender.requests_panel.setLayout(GridLayout(1, 0))
    # 强制重新绘制并验证布局
    extender.requests_panel.revalidate()
    extender.requests_panel.repaint()

    # 标记为已展开状态
    extender.expanded_requests = 1


def collapse(extender, comp):
    comp.setSelectedIndex(0)
    
    # 使用翻译功能设置标签文本
    comp.setTitleAt(2, get_text("expand", "Expand"))

    extender.requests_panel.setLayout(GridLayout(3, 0))

    extender.requests_panel.add(extender.modified_requests_tabs)
    extender.requests_panel.add(extender.original_requests_tabs)
    extender.requests_panel.add(extender.unauthenticated_requests_tabs)

    extender.requests_panel.revalidate()

    extender.expanded_requests = 0


def handle_proxy_message(self, message):
    currentPort = message.getListenerInterface().split(":")[1]
    for i in range(0, self.IFList.getModel().getSize()):
        interceptionFilter = self.IFList.getModel().getElementAt(i)
        interceptionFilterTitle = interceptionFilter.split(":")[0]

        if interceptionFilterTitle == "Drop proxy listener ports":
            portsList = interceptionFilter[27:].split(",")
            portsList = [int(i) for i in portsList]
            if int(currentPort) in portsList:
                message.setInterceptAction(IInterceptedProxyMessage.ACTION_DROP)