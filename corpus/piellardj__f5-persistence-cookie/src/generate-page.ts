import * as fs from "fs";
import * as path from "path";
import { DemopageEmpty } from "webpage-templates";

const data = {
    title: "F5 persistence cookie",
    description: "Tool to decode and craft F5 BIG-IP persistence cookies",
    introduction: [
        "This is a simple tool to decode and craft F5 BIG-IP persistence cookies. They contain the local IP and port of the machine.",
        "The structure of these cookies is explained <a href='https://my.f5.com/manage/s/article/K6917'>here</a>."
    ],
    githubProjectName: "f5-persistence-cookie",
    readme: {
        filepath: path.join(__dirname, "..", "README.md"),
        branchName: "main"
    },
    additionalLinks: [],
    scriptFiles: [
        "script/main.min.js"
    ],
    styleFiles: [
        "css/demo.css"
    ],
    body:
`<div id="error-messages">
    <noscript>You need to enable Javascript to run this experiment.</noscript>
</div>

<div id="mode-chooser">
    <span><input id="mode-0" type="radio" name="mode" value="decode" checked><label for="mode-0">Decode</label></span>
    <span><input id="mode-1" type="radio" name="mode" value="encode"><label for="mode-1">Encode</label></span>
</div>

<div class="section">
    <div class="section-contents" id="decode-contents">
        <div class="controls-block">
            <div class="controls-block-item">
                <div class="control-label">Cookie value:</div>
                <div class="control-container"><input type="text" id="cookie-value" size="40" value="1677787402.36895.0000"></input></div>
            </div>
            <div class="controls-block-spacer"></div>
            <div class="controls-block-item" id="route-domain-span-container" style="display:none;">
                <div class="control-label">Route domain:</div>
                <div class="control-container"><span id="route-domain-span" disabled></span></div>
            </div>
            <div class="controls-block-item">
                <div class="control-label">IP:</div>
                <div class="control-container"><span id="ip-span"></span></div>
            </div>
            <div class="controls-block-item">
                <div class="control-label">Port:</div>
                <div class="control-container"><span id="port-span"></span></div>
            </div>
        </div>
    </div>
    <div class="section-contents" id="encode-contents" style="display:none;">
        <div class="controls-block">
            <div class="controls-block-item">
                <div class="control-label">Enable route domain:</div>
                <div class="control-container"><input type="checkbox" id="enable-route-domain"></input></div>
            </div>
            <div class="controls-block-item">
                <div class="control-label">Route domain:</div>
                <div class="control-container"><input type="number" min="0" max="100" value="1" id="route-domain" disabled></input></div>
            </div>
            <div class="controls-block-item">
                <div class="control-label">IP:</div>
                <div class="control-container"><input type="text" size="15" placeholder="XXX.XXX.XXX.XXX" value="10.1.1.100" id="ip"></input></div>
            </div>
            <div class="controls-block-item">
                <div class="control-label">Port:</div>
                <div class="control-container"><input type="number" min="0" max="65535" value="8080" id="port"></input></div>
            </div>
            <div class="controls-block-spacer"></div>
            <div class="controls-block-item">
                <div class="control-label">Cookie value:</div>
                <div class="control-container"><span id="computed-result"></span></div>
            </div>
        </div>
    </div>
</div>`,
};

const DEST_DIR = path.resolve(__dirname, "..", "docs");

const buildResult = DemopageEmpty.build(data, DEST_DIR);

// disable linting on this file because it is generated
buildResult.pageScriptDeclaration = "/* tslint:disable */\n" + buildResult.pageScriptDeclaration;

const SCRIPT_DECLARATION_FILEPATH = path.resolve(__dirname, ".", "ts", "page-interface-generated.ts");
fs.writeFileSync(SCRIPT_DECLARATION_FILEPATH, buildResult.pageScriptDeclaration);

const sourceCss = path.resolve(__dirname, "static", "css", "demo.css");
const destinationCss = path.resolve(__dirname, "..", "docs", "css", "demo.css");

fs.copyFileSync(sourceCss, destinationCss);
