import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import path from "path";

function readWorkspaceFile(relativePath: string): string {
  return readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

describe("macOS 发布工作流", () => {
  it("应该使用 Node 24 运行时兼容的 Actions 主版本", () => {
    const workflow = readWorkspaceFile(".github/workflows/build.yml");

    expect(workflow).toContain("uses: actions/checkout@v6");
    expect(workflow).toContain("uses: pnpm/action-setup@v6");
    expect(workflow).toContain("uses: actions/setup-node@v6");
    expect(workflow).toContain("uses: actions/upload-artifact@v7");
    expect(workflow).toContain("uses: actions/download-artifact@v6");
    expect(workflow).toContain("uses: softprops/action-gh-release@v3");
  });

  it("应该分别在 Intel 和 Apple Silicon runner 上构建 macOS x64 与 arm64 包", () => {
    const workflow = readWorkspaceFile(".github/workflows/build.yml");

    expect(workflow).toContain("platform: mac");
    expect(workflow).toContain("os: macos-15-intel");
    expect(workflow).toContain("arch: x64");
    expect(workflow).toContain("os: macos-15");
    expect(workflow).toContain("arch: arm64");
    expect(workflow).toContain("npx electron-builder --mac --${{ matrix.arch }} --publish never");
    expect(workflow).not.toContain("npx electron-builder --mac --x64 --arm64 --publish never");
  });

  it("应该在发布前校验 better-sqlite3 原生模块与 macOS 目标架构一致", () => {
    const workflow = readWorkspaceFile(".github/workflows/build.yml");

    expect(workflow).toContain("better-sqlite3/build/Release/better_sqlite3.node");
    expect(workflow).toContain("file \"$native_module\" | tee \"dist/better-sqlite3-${{ matrix.arch }}.txt\"");
    expect(workflow).toContain("grep -Eq \"x86_64|x86_64h\" \"dist/better-sqlite3-${{ matrix.arch }}.txt\"");
    expect(workflow).toContain("grep -q \"arm64\" \"dist/better-sqlite3-${{ matrix.arch }}.txt\"");
  });

  it("应该将拆分构建后的 macOS 更新元数据合并为 latest-mac.yml", () => {
    const workflow = readWorkspaceFile(".github/workflows/build.yml");

    expect(workflow).toContain("mv \"dist/latest-mac.yml\" \"dist/latest-mac-${{ matrix.arch }}.yml\"");
    expect(workflow).toContain("Merge macOS update metadata");
    expect(workflow).toContain("artifacts/latest-mac.yml");
  });

  it("应该仅在 macOS 代码签名 secrets 存在时注入并校验签名", () => {
    const workflow = readWorkspaceFile(".github/workflows/build.yml");

    expect(workflow).toContain("SIGNING_CSC_LINK: ${{ secrets.CSC_LINK }}");
    expect(workflow).toContain('if [ -n "$SIGNING_CSC_LINK" ]; then');
    expect(workflow).toContain('echo "CSC_LINK=$SIGNING_CSC_LINK" >> "$GITHUB_ENV"');
    expect(workflow).toContain('echo "MAC_SIGNING_ENABLED=true" >> "$GITHUB_ENV"');
    expect(workflow).toContain('echo "MAC_SIGNING_ENABLED=false" >> "$GITHUB_ENV"');
    expect(workflow).toContain('if [ "$MAC_SIGNING_ENABLED" != "true" ]; then');
    expect(workflow).toContain("codesign --verify --deep --strict --verbose=2");
  });

  it("应该为 macOS 构建启用 hardened runtime 和 entitlements", () => {
    const builderConfig = readWorkspaceFile("electron-builder.yml");

    expect(builderConfig).toContain("hardenedRuntime: true");
    expect(builderConfig).toContain("gatekeeperAssess: false");
    expect(builderConfig).toContain("type: distribution");
    expect(builderConfig).toContain("entitlements: resources/entitlements.mac.plist");
    expect(builderConfig).toContain("entitlementsInherit: resources/entitlements.mac.plist");
  });

  it("应该提供 Electron 所需的 macOS entitlements", () => {
    const entitlements = readWorkspaceFile("resources/entitlements.mac.plist");

    expect(entitlements).toContain("com.apple.security.cs.allow-jit");
    expect(entitlements).toContain("com.apple.security.cs.allow-unsigned-executable-memory");
    expect(entitlements).toContain("com.apple.security.cs.disable-library-validation");
  });
});
