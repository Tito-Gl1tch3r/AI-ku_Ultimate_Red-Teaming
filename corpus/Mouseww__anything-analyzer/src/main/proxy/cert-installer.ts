import { exec } from "child_process";
import { existsSync, readFileSync } from "fs";
import { platform } from "os";

/**
 * CertInstaller — Cross-platform CA certificate installation/removal
 * using elevated privilege execution.
 *
 * Windows: certutil  (UAC prompt via runas)
 * macOS:   security  (password prompt via osascript)
 * Linux:   distro-specific system trust stores (pkexec/sudo prompt)
 */

interface CertResult {
  success: boolean;
  error?: string;
}

// Dynamically import @vscode/sudo-prompt to avoid bundling issues
async function getSudoPrompt(): Promise<typeof import("@vscode/sudo-prompt")> {
  return await import("@vscode/sudo-prompt");
}

function execPromise(cmd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    exec(cmd, { timeout: 30_000 }, (err, stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message));
      else resolve(stdout);
    });
  });
}

function sudoExec(cmd: string, name: string): Promise<string> {
  return new Promise(async (resolve, reject) => {
    const sudo = await getSudoPrompt();
    sudo.exec(cmd, { name }, (err?: Error, stdout?: string | Buffer) => {
      if (err) reject(err);
      else resolve(String(stdout ?? ""));
    });
  });
}

async function commandExists(command: string): Promise<boolean> {
  try {
    await execPromise(`command -v ${command}`);
    return true;
  } catch {
    return false;
  }
}

function isArchLikeLinux(): boolean {
  if (existsSync("/etc/arch-release")) return true;

  try {
    const osRelease = readFileSync("/etc/os-release", "utf-8").toLowerCase();
    return /(^|\n)id(_like)?=.*\b(arch|manjaro|endeavouros|garuda)\b/.test(
      osRelease,
    );
  } catch {
    return false;
  }
}

export class CertInstaller {
  /**
   * Install CA certificate to the system trust store (requires elevation).
   */
  static async install(certPath: string): Promise<CertResult> {
    try {
      const os = platform();

      if (os === "win32") {
        await sudoExec(
          `certutil -addstore Root "${certPath}"`,
          "Anything Analyzer",
        );
      } else if (os === "darwin") {
        await sudoExec(
          `security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "${certPath}"`,
          "Anything Analyzer",
        );
      } else {
        await this.installLinux(certPath);
      }

      return { success: true };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  }

  /**
   * Remove CA certificate from the system trust store (requires elevation).
   */
  static async uninstall(certPath: string): Promise<CertResult> {
    try {
      const os = platform();

      if (os === "win32") {
        await sudoExec(
          `certutil -delstore Root "Anything Analyzer CA"`,
          "Anything Analyzer",
        );
      } else if (os === "darwin") {
        await sudoExec(
          `security remove-trusted-cert -d "${certPath}"`,
          "Anything Analyzer",
        );
      } else {
        await this.uninstallLinux(certPath);
      }

      return { success: true };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  }

  /**
   * Check whether the CA certificate is currently trusted by the system.
   */
  static async isInstalled(_certPath: string): Promise<boolean> {
    try {
      const os = platform();

      if (os === "win32") {
        const out = await execPromise(
          `certutil -store Root "Anything Analyzer CA"`,
        );
        return out.includes("Anything Analyzer CA");
      } else if (os === "darwin") {
        const out = await execPromise(
          `security find-certificate -c "Anything Analyzer CA" /Library/Keychains/System.keychain`,
        );
        return out.includes("Anything Analyzer CA");
      } else {
        return this.isLinuxInstalled();
      }
    } catch {
      return false;
    }
  }

  private static async installLinux(certPath: string): Promise<void> {
    if (isArchLikeLinux()) {
      const dest =
        "/etc/ca-certificates/trust-source/anchors/anything-analyzer.crt";
      const refreshCmd = await this.getLinuxTrustRefreshCommand();
      await sudoExec(
        `mkdir -p /etc/ca-certificates/trust-source/anchors && cp "${certPath}" "${dest}" && ${refreshCmd}`,
        "Anything Analyzer",
      );
      return;
    }

    if (await commandExists("update-ca-certificates")) {
      const dest = "/usr/local/share/ca-certificates/anything-analyzer.crt";
      await sudoExec(
        `cp "${certPath}" "${dest}" && update-ca-certificates`,
        "Anything Analyzer",
      );
      return;
    }

    if (await commandExists("update-ca-trust")) {
      const dest = "/etc/pki/ca-trust/source/anchors/anything-analyzer.crt";
      await sudoExec(
        `mkdir -p /etc/pki/ca-trust/source/anchors && cp "${certPath}" "${dest}" && update-ca-trust extract`,
        "Anything Analyzer",
      );
      return;
    }

    if (await commandExists("trust")) {
      await sudoExec(
        `trust anchor --store "${certPath}" && trust extract-compat`,
        "Anything Analyzer",
      );
      return;
    }

    throw new Error("No supported Linux CA trust tool found");
  }

  private static async uninstallLinux(certPath: string): Promise<void> {
    if (isArchLikeLinux()) {
      const refreshCmd = await this.getLinuxTrustRefreshCommand();
      await sudoExec(
        `rm -f /etc/ca-certificates/trust-source/anchors/anything-analyzer.crt && ${refreshCmd}`,
        "Anything Analyzer",
      );
      return;
    }

    if (await commandExists("update-ca-certificates")) {
      await sudoExec(
        `rm -f /usr/local/share/ca-certificates/anything-analyzer.crt && update-ca-certificates`,
        "Anything Analyzer",
      );
      return;
    }

    if (await commandExists("update-ca-trust")) {
      await sudoExec(
        `rm -f /etc/pki/ca-trust/source/anchors/anything-analyzer.crt && update-ca-trust extract`,
        "Anything Analyzer",
      );
      return;
    }

    if (await commandExists("trust")) {
      await sudoExec(
        `trust anchor --remove "${certPath}" && trust extract-compat`,
        "Anything Analyzer",
      );
      return;
    }

    throw new Error("No supported Linux CA trust tool found");
  }

  private static async getLinuxTrustRefreshCommand(): Promise<string> {
    if (await commandExists("update-ca-trust")) {
      return "update-ca-trust extract";
    }
    if (await commandExists("trust")) {
      return "trust extract-compat";
    }
    throw new Error("No supported Linux CA trust refresh tool found");
  }

  private static isLinuxInstalled(): boolean {
    return (
      existsSync(
        "/etc/ca-certificates/trust-source/anchors/anything-analyzer.crt",
      ) ||
      existsSync("/usr/local/share/ca-certificates/anything-analyzer.crt") ||
      existsSync("/etc/pki/ca-trust/source/anchors/anything-analyzer.crt")
    );
  }
}
