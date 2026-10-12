#!/usr/bin/env python3
# coding: utf-8

"""
@File   : Autorize.py
@Author : sule01u
@Date   : 2024/10/10
@Desc   :
"""

from burp import IBurpExtender, IHttpListener, IProxyListener
from authorization.authorization import handle_message
from helpers.initiator import Initiator
from helpers.filters import handle_proxy_message

# 导入语言管理器
from localization.language_manager import get_text


class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()

        # 使用本地化文本设置扩展名称
        callbacks.setExtensionName(get_text("extension_name", "AutorizePro"))

        initiator = Initiator(self)

        initiator.init_constants()

        initiator.draw_all()

        initiator.implement_all()

        initiator.init_ui()

        initiator.print_welcome_message()

        return

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        handle_message(self, toolFlag, messageIsRequest, messageInfo)

    def processProxyMessage(self, messageIsRequest, message):
        handle_proxy_message(self, message)