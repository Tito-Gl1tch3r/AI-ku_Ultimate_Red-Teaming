// as described in https://my.f5.com/manage/s/article/K6917

function decodeCookie(encoded: string): CookieInfos | null {
    return decodeCookieNewFormat(encoded) || decodeCookieOldFormat(encoded);
}

function decodeCookieOldFormat(encoded: string): CookieInfos | null {
    const match = encoded.match(/^([0-9]+)\.([0-9]+).0000$/);
    if (match) {
        const encodedIP = +match[1]!;
        const encodedPort = +match[2]!;

        /* tslint:disable no-bitwise */
        const ipAsArray = [
            (encodedIP >> 0) & 0xFF,
            (encodedIP >> 8) & 0xFF,
            (encodedIP >> 16) & 0xFF,
            (encodedIP >> 24) & 0xFF,
        ];
        const decodedIP = ipAsArray.join(".");
        const decodedPort = (encodedPort >> 8) + ((encodedPort & 0xFF) << 8);

        return {
            ip: decodedIP,
            port: decodedPort,
        };
    }
    return null;
}

function decodeCookieNewFormat(encoded: string): CookieInfos | null {
    const match = encoded.match(/^rd([0-9]+)o00000000000000000000ffff([a-fA-F0-9]+)o([0-9]+)$/);
    if (match) {
        const routeDomain = +match[1]!;
        const hexaIP = match[2]!;
        const numericIP = Number(`0x${hexaIP}`);
        const ipAsArray = [
            (numericIP >> 24) & 0xFF,
            (numericIP >> 16) & 0xFF,
            (numericIP >> 8) & 0xFF,
            (numericIP >> 0) & 0xFF,
        ];
        const decodedIP = ipAsArray.join(".");
        const port = +match[3]!;

        return {
            ip: decodedIP,
            port,
            routeDomain,
        };
    }
    return null;
}

function parseIp(asString: string): [number, number, number, number] | null {
    asString = asString.trim();
    const match = asString.match(/^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$/);
    if (!match) {
        return null;
    }

    const parts: [number, number, number, number] = [
        +match[1],
        +match[2],
        +match[3],
        +match[4],
    ];

    for (const part of parts) {
        if (isNaN(part) || part < 0 || part > 255) {
            return null;
        }
    }

    return parts;
}

type CookieInfos = {
    routeDomain?: number;
    ip: string;
    port: number;
};

function encodeCookie(infos: CookieInfos): string | null {
    const parsedIp = parseIp(infos.ip);
    if (parsedIp !== null) {
        if (typeof infos.routeDomain === "number") {
            const ipAsNumber = parsedIp[3] + 256 * (parsedIp[2] + 256 * (parsedIp[1] + 256 * parsedIp[0]));
            const encodedIP = ipAsNumber.toString(16).padStart(8, "0");
            return `rd${infos.routeDomain}o00000000000000000000ffff${encodedIP}o${infos.port}`;
        } else {
            const encodedIP = (parsedIp[0] + 256 * (parsedIp[1] + 256 * (parsedIp[2] + 256 * parsedIp[3]))).toFixed();
            const encodedPort = (((infos.port & 0xFF) << 8) + ((infos.port >> 8) & 0xFF)).toFixed();
            return `${encodedIP}.${encodedPort}.0000`;
        }
    }
    return null;
}

export type {
    CookieInfos,
};
export {
    decodeCookie,
    encodeCookie,
    parseIp,
};

