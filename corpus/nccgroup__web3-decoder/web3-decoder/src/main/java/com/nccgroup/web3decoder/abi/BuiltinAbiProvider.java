package com.nccgroup.web3decoder.abi;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * Serves ABIs that are bundled with the extension. Useful for canonical
 * cross-chain contracts (e.g. Multicall3 at 0xca11bde0...) whose ABI is the
 * same on every chain regardless of explorer availability.
 *
 * Lookups are keyed by lowercase contract address.
 */
public final class BuiltinAbiProvider implements IAbiProvider {

    private static final String MULTICALL3_ADDRESS = "0xca11bde05977b3631167028862be2a173976ca11";
    private static final String MULTICALL3_RESOURCE = "/builtin-abis/multicall3.json";

    private static final Map<String, String> BUILTIN_ABIS = loadBuiltinAbis();

    private static Map<String, String> loadBuiltinAbis() {
        Map<String, String> map = new HashMap<>();
        String multicall3 = readResource(MULTICALL3_RESOURCE);
        if (multicall3 != null) {
            map.put(MULTICALL3_ADDRESS, multicall3);
        }
        return map;
    }

    private static String readResource(String path) {
        try (InputStream in = BuiltinAbiProvider.class.getResourceAsStream(path)) {
            if (in == null) {
                return null;
            }
            StringBuilder sb = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append('\n');
                }
            }
            return sb.toString();
        } catch (IOException e) {
            return null;
        }
    }

    @Override
    public String getAbi(String contractAddress) {
        if (contractAddress == null) {
            return null;
        }
        return BUILTIN_ABIS.get(contractAddress.toLowerCase());
    }
}
