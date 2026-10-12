import * as Engine from "./engine";

describe("parseIp valid", function () {
    function testValidIp(i1: number, i2: number, i3: number, i4: number): void {
        const ipAsString = `${i1}.${i2}.${i3}.${i4}`;
        test(ipAsString, () => {
            expect(Engine.parseIp(ipAsString)?.toString()).toBe(`${i1},${i2},${i3},${i4}`);
        });
    }

    testValidIp(0, 0, 0, 0);
    testValidIp(192, 0, 0, 0);
    testValidIp(10, 31, 51, 108);
    testValidIp(255, 255, 255, 255);
});

describe("parseIp invalid", function () {
    function testInvalidIp(invalidIp: string): void {
        test(invalidIp, () => {
            expect(Engine.parseIp(invalidIp)).toBeNull();
        });
    }
    testInvalidIp("");
    testInvalidIp("haha");
    testInvalidIp("-1.0.0.0");
    testInvalidIp("256.0.0.0");
    testInvalidIp("0.256.0.0");
    testInvalidIp("0.0.256.0");
    testInvalidIp("0.0.0.256");
});


describe("decodeCookie", function () {
    function testCookie(cookie: string, cookieInfos: Engine.CookieInfos): void {
        test(cookie, () => {
            const actual = JSON.stringify(Engine.decodeCookie(cookie));
            const expected = JSON.stringify(cookieInfos);
            expect(actual).toBe(expected);
        });
    }
    testCookie("1677787402.36895.0000", { ip: "10.1.1.100", port: 8080 });
    testCookie("1375804938.20480.0000", { ip: "10.30.1.82", port: 80 });
    testCookie("1040522762.20480.0000", { ip: "10.30.5.62", port: 80 });

    testCookie("rd5o00000000000000000000ffffc0000201o80", { ip: "192.0.2.1", port: 80, routeDomain: 5 });
    testCookie("rd1o00000000000000000000ffff0a2c6825o80", { ip: "10.44.104.37", port: 80, routeDomain: 1 });
});

describe("encodeCookie", function () {
    function testCookie(infos: Engine.CookieInfos, cookie: string): void {
        test(cookie, () => {
            expect(Engine.encodeCookie(infos)).toBe(cookie);
        });
    }
    testCookie({ ip: "10.1.1.100", port: 8080 }, "1677787402.36895.0000");
    testCookie({ ip: "10.30.1.82", port: 80 }, "1375804938.20480.0000");
    testCookie({ ip: "10.30.5.62", port: 80 }, "1040522762.20480.0000");

    testCookie({ ip: "192.0.2.1", port: 80, routeDomain: 5 }, "rd5o00000000000000000000ffffc0000201o80");
    testCookie({ ip: "10.44.104.37", port: 80, routeDomain: 1 }, "rd1o00000000000000000000ffff0a2c6825o80");
});

