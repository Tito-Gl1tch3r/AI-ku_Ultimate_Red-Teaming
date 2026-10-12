
class Adapter:
    def __init__(self, adaptee):
        self.adaptee = adaptee

    def configure_proxy(self, enable):
        return self.adaptee.configure_proxy(enable)
    
    def check_and_restore_source_lines(self):
        return self.adaptee.check_and_restore_source_lines()

    def watch_proxy_env_file_and_system_proxy(self):
        return self.adaptee.watch_proxy_env_file_and_system_proxy()
    
    def install_cert_to_keychain(self):
        return self.adaptee.install_cert_to_keychain()
    
    def remove_cert_from_keychain(self):
        return self.adaptee.remove_cert_from_keychain()
    
    def write_launch_agent(self):
        return self.adaptee.write_launch_agent()
    
    def unload_and_remove_launch_agent(self):
        return self.adaptee.unload_and_remove_launch_agent()