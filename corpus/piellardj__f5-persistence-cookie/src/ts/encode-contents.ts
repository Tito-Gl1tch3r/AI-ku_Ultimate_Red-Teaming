import { encodeCookie, parseIp, type CookieInfos } from "./engine/engine";

class EncodeContents {
    private readonly container = document.getElementById("encode-contents")!;
    private readonly enableRouteDomainCheckbox = document.getElementById("enable-route-domain") as HTMLInputElement;
    private readonly routeDomainInput = document.getElementById("route-domain") as HTMLInputElement;
    private readonly ipInput = document.getElementById("ip") as HTMLInputElement;
    private readonly portInput = document.getElementById("port") as HTMLInputElement;
    private readonly computedResultSpan = document.getElementById("computed-result") as HTMLElement;

    private encoded: string | null = null;

    public constructor() {
        const onChange = () => this.onChange();
        this.enableRouteDomainCheckbox.addEventListener("change", onChange);
        this.routeDomainInput.addEventListener("change", onChange);
        this.routeDomainInput.addEventListener("keyup", onChange);
        this.ipInput.addEventListener("change", onChange);
        this.ipInput.addEventListener("keyup", onChange);
        this.portInput.addEventListener("change", onChange);
        this.portInput.addEventListener("keyup", onChange);
        this.onChange();
    }

    public getEncoded(): string | null {
        return this.encoded;
    }

    public set visibility(visible: boolean) {
        this.container.style.display = visible ? "" : "none";
    }

    public set cookiesInfo(cookieInfos: CookieInfos) {
        if (typeof cookieInfos.routeDomain === "number") {
            this.enableRouteDomainCheckbox.checked = true;
            this.routeDomainInput.value = cookieInfos.routeDomain.toFixed();
        } else {
            this.enableRouteDomainCheckbox.checked = false;
        }
        this.ipInput.value = cookieInfos.ip;
        this.portInput.value = cookieInfos.port.toFixed();
        this.onChange();
    }

    private onChange(): void {
        this.routeDomainInput.disabled = !this.enableRouteDomainCheckbox.checked;

        this.encoded = null;

        const rawIP = this.ipInput.value.trim();
        if (parseIp(rawIP)) {
            const cookieInfos: CookieInfos = {
                ip: rawIP,
                port: +this.portInput.value,
            };
            if (this.enableRouteDomainCheckbox.checked) {
                cookieInfos.routeDomain = +this.routeDomainInput.value;
            }
            this.encoded = encodeCookie(cookieInfos);
        }

        this.computedResultSpan.textContent = this.encoded || "<invalid input>";
    }
}

export {
    EncodeContents,
};

