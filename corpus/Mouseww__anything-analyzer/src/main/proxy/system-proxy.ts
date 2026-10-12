import { exec } from "child_process";
import { platform } from "os";

/**
 * SystemProxy — Set/unset the OS-level HTTP/HTTPS proxy.
 *
 * All operations target the **current user** level, so no elevation is needed.
 *
 * - Windows: registry HKCU\...\Internet Settings
 * - macOS:   networksetup
 * - Linux:   gsettings (GNOME)
 */

interface ProxyResult {
  success: boolean;
  error?: string;
}

function execPromise(cmd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    exec(cmd, { timeout: 10_000 }, (err, stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message));
      else resolve(stdout.trim());
    });
  });
}

/** Saved state before we touched the system proxy, for restoration. */
let savedState: { platform: string; data: Record<string, string> } | null =
  null;

export class SystemProxy {
  /**
   * Set the system HTTP/HTTPS proxy to localhost:<port>.
   * Saves original proxy state for later restoration.
   */
  static async enable(port: number): Promise<ProxyResult> {
    try {
      const os = platform();

      if (os === "win32") {
        await this.enableWindows(port);
      } else if (os === "darwin") {
        await this.enableMacOS(port);
      } else {
        await this.enableLinux(port);
      }

      return { success: true };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  }

  /**
   * Restore the system proxy to its original state.
   */
  static async disable(): Promise<ProxyResult> {
    try {
      const os = platform();

      if (os === "win32") {
        await this.disableWindows();
      } else if (os === "darwin") {
        await this.disableMacOS();
      } else {
        await this.disableLinux();
      }

      savedState = null;
      return { success: true };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  }

  /**
   * Check whether the system proxy currently points to our MITM proxy.
   */
  static async isEnabled(port: number): Promise<boolean> {
    try {
      const os = platform();
      if (os === "win32") {
        const out = await execPromise(
          `reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable`,
        );
        const serverOut = await execPromise(
          `reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer`,
        );
        return (
          out.includes("0x1") &&
          serverOut.includes(`localhost:${port}`)
        );
      } else if (os === "darwin") {
        const service = await this.getActiveMacService();
        const out = await execPromise(
          `networksetup -getwebproxy "${service}"`,
        );
        return (
          out.includes("Enabled: Yes") &&
          out.includes(`Port: ${port}`) &&
          out.includes("Server: localhost")
        );
      } else {
        const mode = await execPromise(
          `gsettings get org.gnome.system.proxy mode`,
        );
        const host = await execPromise(
          `gsettings get org.gnome.system.proxy.http host`,
        );
        return mode.includes("manual") && host.includes("localhost");
      }
    } catch {
      return false;
    }
  }

  // ---- Windows ----

  private static async enableWindows(port: number): Promise<void> {
    const regPath = `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings`;

    // Save current state
    try {
      const enableOut = await execPromise(
        `reg query "${regPath}" /v ProxyEnable`,
      );
      const serverOut = await execPromise(
        `reg query "${regPath}" /v ProxyServer`,
      ).catch(() => "");
      const overrideOut = await execPromise(
        `reg query "${regPath}" /v ProxyOverride`,
      ).catch(() => "");

      savedState = {
        platform: "win32",
        data: {
          enable: enableOut,
          server: serverOut,
          override: overrideOut,
        },
      };
    } catch {
      // No existing proxy — that's fine
      savedState = { platform: "win32", data: { enable: "0x0" } };
    }

    await execPromise(
      `reg add "${regPath}" /v ProxyEnable /t REG_DWORD /d 1 /f`,
    );
    await execPromise(
      `reg add "${regPath}" /v ProxyServer /t REG_SZ /d "localhost:${port}" /f`,
    );
    await execPromise(
      `reg add "${regPath}" /v ProxyOverride /t REG_SZ /d "localhost;127.0.0.1;<local>" /f`,
    );

    // Notify the system that proxy settings have changed
    // InternetSetOption with INTERNET_OPTION_REFRESH
    await execPromise(
      `powershell -Command "[System.Runtime.InteropServices.RuntimeEnvironment]::FromGS 2>$null; $sig='[DllImport(\\"wininet.dll\\")]public static extern bool InternetSetOption(IntPtr a,int b,IntPtr c,int d);'; $type=Add-Type -MemberDefinition $sig -Name WinInet -PassThru; $type::InternetSetOption(0,39,0,0); $type::InternetSetOption(0,37,0,0)"`,
    ).catch(() => {});
  }

  private static async disableWindows(): Promise<void> {
    const regPath = `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings`;
    await execPromise(
      `reg add "${regPath}" /v ProxyEnable /t REG_DWORD /d 0 /f`,
    );

    // Notify system
    await execPromise(
      `powershell -Command "$sig='[DllImport(\\"wininet.dll\\")]public static extern bool InternetSetOption(IntPtr a,int b,IntPtr c,int d);'; $type=Add-Type -MemberDefinition $sig -Name WinInet2 -PassThru; $type::InternetSetOption(0,39,0,0); $type::InternetSetOption(0,37,0,0)"`,
    ).catch(() => {});
  }

  // ---- macOS ----

  private static async getActiveMacService(): Promise<string> {
    const out = await execPromise(
      `networksetup -listnetworkserviceorder | grep -B1 "$(route get default 2>/dev/null | grep interface | awk '{print $2}')" | head -1 | sed 's/^([0-9]*) //'`,
    ).catch(() => "");
    // Fallback to common service names
    if (!out || out.length < 2) {
      const services = await execPromise(`networksetup -listallnetworkservices`);
      if (services.includes("Wi-Fi")) return "Wi-Fi";
      if (services.includes("Ethernet")) return "Ethernet";
      return "Wi-Fi";
    }
    return out.trim();
  }

  private static async enableMacOS(port: number): Promise<void> {
    const service = await this.getActiveMacService();
    savedState = { platform: "darwin", data: { service } };

    await execPromise(
      `networksetup -setwebproxy "${service}" localhost ${port}`,
    );
    await execPromise(
      `networksetup -setsecurewebproxy "${service}" localhost ${port}`,
    );
    await execPromise(
      `networksetup -setproxybypassdomains "${service}" localhost 127.0.0.1`,
    );
  }

  private static async disableMacOS(): Promise<void> {
    const service =
      savedState?.platform === "darwin"
        ? savedState.data.service || "Wi-Fi"
        : await this.getActiveMacService();

    await execPromise(`networksetup -setwebproxystate "${service}" off`);
    await execPromise(`networksetup -setsecurewebproxystate "${service}" off`);
  }

  // ---- Linux (GNOME) ----

  private static async enableLinux(port: number): Promise<void> {
    savedState = { platform: "linux", data: {} };

    await execPromise(
      `gsettings set org.gnome.system.proxy mode 'manual'`,
    );
    await execPromise(
      `gsettings set org.gnome.system.proxy.http host 'localhost'`,
    );
    await execPromise(
      `gsettings set org.gnome.system.proxy.http port ${port}`,
    );
    await execPromise(
      `gsettings set org.gnome.system.proxy.https host 'localhost'`,
    );
    await execPromise(
      `gsettings set org.gnome.system.proxy.https port ${port}`,
    );
    await execPromise(
      `gsettings set org.gnome.system.proxy ignore-hosts "['localhost', '127.0.0.1', '::1']"`,
    );
  }

  private static async disableLinux(): Promise<void> {
    await execPromise(
      `gsettings set org.gnome.system.proxy mode 'none'`,
    );
  }
}
