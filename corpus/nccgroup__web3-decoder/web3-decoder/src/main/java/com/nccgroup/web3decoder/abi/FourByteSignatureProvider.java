package com.nccgroup.web3decoder.abi;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.HttpService;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.logging.Logging;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public class FourByteSignatureProvider {
    private static final String HOST = "api.4byte.sourcify.dev";
    private static final String LOOKUP_PATH = "/signature-database/v1/lookup";
    private static final Pattern SELECTOR_PATTERN = Pattern.compile("^0x[0-9a-fA-F]{8}$");

    private final MontoyaApi api;
    private final Logging logging;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public FourByteSignatureProvider(MontoyaApi api) {
        this.api = api;
        this.logging = api.logging();
    }

    public List<String> lookupFunctionSignatures(String selector) {
        String normalizedSelector = selector == null ? "" : selector.trim().toLowerCase();
        if (!SELECTOR_PATTERN.matcher(normalizedSelector).matches()) {
            return List.of();
        }

        try {
            String encodedSelector = URLEncoder.encode(normalizedSelector, StandardCharsets.UTF_8);
            String pathAndQuery = LOOKUP_PATH + "?function=" + encodedSelector + "&filter=true";
            HttpService service = HttpService.httpService("https://" + HOST);
            JSONObject response = executeGet(service, pathAndQuery);
            if (response == null || !response.optBoolean("ok", false)) {
                return List.of();
            }

            JSONObject result = response.optJSONObject("result");
            if (result == null) {
                return List.of();
            }

            JSONObject functionObject = result.optJSONObject("function");
            if (functionObject == null) {
                return List.of();
            }

            JSONArray signatures = functionObject.optJSONArray(normalizedSelector);
            if (signatures == null) {
                signatures = functionObject.optJSONArray(normalizedSelector.toUpperCase());
            }
            if (signatures == null) {
                return List.of();
            }

            LinkedHashSet<String> verified = new LinkedHashSet<>();
            LinkedHashSet<String> other = new LinkedHashSet<>();
            for (int i = 0; i < signatures.length(); i++) {
                JSONObject candidate = signatures.optJSONObject(i);
                if (candidate == null) {
                    continue;
                }
                String name = candidate.optString("name", "").trim();
                if (name.isEmpty()) {
                    continue;
                }
                if (candidate.optBoolean("hasVerifiedContract", false)) {
                    verified.add(name);
                } else {
                    other.add(name);
                }
            }

            List<String> ordered = new ArrayList<>(verified);
            for (String sig : other) {
                if (!ordered.contains(sig)) {
                    ordered.add(sig);
                }
            }
            return ordered;
        } catch (Exception e) {
            logging.logToError("4byte lookup failed for selector " + normalizedSelector + ": " + e.getMessage());
            return List.of();
        }
    }

    public String buildSyntheticAbiFromSignature(String signature) throws Exception {
        String clean = signature == null ? "" : signature.replaceAll("\\s+", "");
        int openParen = clean.indexOf('(');
        int closeParen = clean.lastIndexOf(')');
        if (openParen <= 0 || closeParen != clean.length() - 1 || closeParen < openParen) {
            throw new IllegalArgumentException("Invalid function signature from 4byte: " + signature);
        }

        String functionName = clean.substring(0, openParen);
        String paramsSegment = clean.substring(openParen + 1, closeParen);
        List<String> parameterTypes = splitTopLevel(paramsSegment);

        List<Map<String, Object>> inputs = new ArrayList<>();
        for (int i = 0; i < parameterTypes.size(); i++) {
            String parameterType = parameterTypes.get(i);
            if (parameterType.isBlank()) {
                continue;
            }
            inputs.add(parseInputParameter(parameterType, "param" + i));
        }

        Map<String, Object> functionDefinition = Map.of(
                "type", "function",
                "name", functionName,
                "inputs", inputs,
                "outputs", List.of()
        );
        return objectMapper.writeValueAsString(List.of(functionDefinition));
    }

    private Map<String, Object> parseInputParameter(String typeExpression, String paramName) {
        String clean = typeExpression.replaceAll("\\s+", "");
        if (!clean.startsWith("(")) {
            return Map.of("name", paramName, "type", clean);
        }

        int tupleClose = findMatchingParen(clean, 0);
        if (tupleClose <= 0) {
            throw new IllegalArgumentException("Invalid tuple type in 4byte signature: " + typeExpression);
        }

        String tupleInner = clean.substring(1, tupleClose);
        String suffix = clean.substring(tupleClose + 1); // array suffixes, if any

        List<String> componentTypes = splitTopLevel(tupleInner);
        List<Map<String, Object>> components = new ArrayList<>();
        for (int i = 0; i < componentTypes.size(); i++) {
            String componentType = componentTypes.get(i);
            if (componentType.isBlank()) {
                continue;
            }
            components.add(parseInputParameter(componentType, "param" + i));
        }

        return Map.of(
                "name", paramName,
                "type", "tuple" + suffix,
                "components", components
        );
    }

    private List<String> splitTopLevel(String input) {
        if (input == null || input.isEmpty()) {
            return List.of();
        }
        List<String> parts = new ArrayList<>();
        int depth = 0;
        int start = 0;
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);
            if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth < 0) {
                    throw new IllegalArgumentException("Malformed type expression: " + input);
                }
            } else if (c == ',' && depth == 0) {
                parts.add(input.substring(start, i));
                start = i + 1;
            }
        }
        parts.add(input.substring(start));
        return parts;
    }

    private int findMatchingParen(String value, int openIndex) {
        int depth = 0;
        for (int i = openIndex; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) {
                    return i;
                }
            }
        }
        return -1;
    }

    private JSONObject executeGet(HttpService service, String pathAndQuery) {
        HttpRequest request = HttpRequest.httpRequest(
                service,
                "GET " + pathAndQuery + " HTTP/1.1\r\nHost: " + service.host() + "\r\nAccept: application/json\r\n\r\n"
        );

        HttpRequestResponse requestResponse = api.http().sendRequest(request);
        HttpResponse response = requestResponse.response();

        if (response.statusCode() != 200) {
            logging.logToError("Failed 4byte lookup via " + service.host() + ". HTTP Status: " + response.statusCode());
            return null;
        }

        return new JSONObject(new JSONTokener(response.bodyToString()));
    }
}
