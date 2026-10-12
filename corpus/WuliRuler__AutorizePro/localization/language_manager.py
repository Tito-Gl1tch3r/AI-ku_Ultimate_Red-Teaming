#!/usr/bin/env python3
# coding: utf-8

"""
@File   : language_manager.py
@Author : sule01u
@Date   : 2024/10/10
@Desc   : 语言管理器，负责国际化文本的获取和语言切换
"""

class LanguageManager:
    def __init__(self):
        self.current_language = "en"
        self.strings = {}
        self.load_language()
        
        try:
            import sys
            if sys.version_info[0] == 2:
                if hasattr(sys, "setdefaultencoding"):
                    reload(sys)
                    sys.setdefaultencoding('utf-8')
                    
            try:
                from java.lang import System
                System.setProperty("file.encoding", "UTF-8")
                System.setProperty("sun.jnu.encoding", "UTF-8")
            except ImportError:
                pass
        except Exception as e:
            print("Warning: Failed to set system encoding: " + str(e))
            pass
    
    def set_language(self, language_code):
        if language_code in ["en", "zh"]:
            self.current_language = language_code
            self.load_language()
            return True
        return False
    
    def load_language(self):
        """根据当前选择的语言加载对应的资源文件"""
        try:
            if self.current_language == "zh":
                from localization.strings_zh import STRINGS
            else:
                from localization.strings_en import STRINGS
            self.strings = STRINGS
            
            if self.current_language == "zh":
                for key, value in self.strings.items():
                    if not isinstance(value, unicode) and isinstance(value, str):
                        try:
                            self.strings[key] = value.decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                self.strings[key] = value.decode('gbk')
                            except:
                                pass
                                
        except ImportError as e:
            print("Warning: Failed to load language file: " + str(e))
            # 如果加载失败，使用默认的英文
            from localization.strings_en import STRINGS
            self.strings = STRINGS
    
    def get_text(self, key, default=""):
        text = self.strings.get(key, default)
        
        if self.current_language == "zh":
            try:
                return self._fix_encoding(text)
            except Exception as e:
                print("Warning: Failed to fix encoding for key {}: {}".format(key, str(e)))
                return text
        return text
    
    def _fix_encoding(self, text):
        if text is None:
            return ""
            
        try:
            from java.lang import String as JavaString
            if isinstance(text, JavaString):
                return text
                
            if isinstance(text, unicode):
                return JavaString(text)
            else:
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1', 'cp936']
                for encoding in encodings:
                    try:
                        return JavaString(text.decode(encoding))
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        continue
                try:
                    return JavaString(text)
                except:
                    return text
                    
        except ImportError:
            return text
        except Exception as e:
            print("Warning: Error in fix_encoding: " + str(e))
            return text

_language_manager = LanguageManager()

def get_language_manager():
    return _language_manager

def get_text(key, default=""):
    return _language_manager.get_text(key, default) 