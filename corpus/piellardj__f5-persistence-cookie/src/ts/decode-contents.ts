import { decodeCookie, type CookieInfos } from "./engine/engine";

class DecodeContents {
    private readonly container = document.getElementById("decode-contents")!;
    private readonly cookieValueInput = document.getElementById("cookie-value") as HTMLInputElement;
    private readonly routeDomainSpanContainer = document.getElementById("route-domain-span-container") as HTMLElement;
    private readonly routeDomainSpan = document.getElementById("route-domain-span") as HTMLElement;
    private readonly ipSpan = document.getElementById("ip-span") as HTMLElement;
    private readonly portSpan = document.getElementById("port-span") as HTMLElement;

    private cookieInfos: CookieInfos | null = null;

    public constructor() {
        const onChange = () => this.onChange();
        this.cookieValueInput.addEventListener("change", onChange);
        this.cookieValueInput.addEventListener("keyup", onChange);
        this.onChange();
    }

    public getCookieInfos(): CookieInfos | null {
        return this.cookieInfos;
    }

    public set visibility(visible: boolean) {
        this.container.style.display = visible ? "" : "none";
    }

    public set cookieValue(cookieValue: string) {
        this.cookieValueInput.value = cookieValue;
        this.onChange()
    }

    private onChange(): void {
        const cookieValue = this.cookieValueInput.value.trim();
        this.cookieInfos = decodeCookie(cookieValue);

        if (this.cookieInfos) {
            this.ipSpan.textContent = this.cookieInfos.ip;
            this.portSpan.textContent = this.cookieInfos.port.toFixed();

            const hasRouteDomain = (typeof this.cookieInfos.routeDomain !== "undefined");
            if (hasRouteDomain) {
                this.routeDomainSpanContainer.style.display = "";
                this.routeDomainSpan.textContent = this.cookieInfos.routeDomain!.toFixed();
            } else {
                this.routeDomainSpanContainer.style.display = "none";
            }
        } else {
            this.ipSpan.textContent = "<invalid input>";
            this.portSpan.textContent = "<invalid input>";
            this.routeDomainSpanContainer.style.display = "none";
        }
    };
}

export {
    DecodeContents,
};

