package com.nccgroup.web3decoder.decoder;

import org.web3j.crypto.RawTransaction;
import org.web3j.crypto.SignedRawTransaction;
import org.web3j.crypto.TransactionDecoder;
import org.web3j.crypto.transaction.type.ITransaction;
import org.web3j.crypto.transaction.type.Transaction1559;
import org.web3j.crypto.transaction.type.Transaction2930;
import org.web3j.crypto.transaction.type.TransactionType;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Decodes a raw, signed Ethereum transaction — the single hex string carried by
 * {@code eth_sendRawTransaction} {@code params[0]} — into a readable envelope:
 * transaction type, chain id, recovered sender, target, nonce, value, gas fields,
 * and the inner calldata.
 *
 * <p>Pure and offline: it wraps web3j's {@link TransactionDecoder} and EC sender
 * recovery, performs no network I/O, and resolves no ABIs. The caller feeds the
 * returned {@code to}/{@code data} into the existing {@code Web3DataDecoder} path.
 *
 * <p>Supports legacy and typed transactions (EIP-2930/1559/4844/7702) as exposed
 * by web3j: 1559/4844/7702 extend {@link Transaction1559}, which extends
 * {@link Transaction2930}, so chain id and fee fields are read by {@code instanceof}.
 */
public final class RawTransactionDecoder {

    private RawTransactionDecoder() {
    }

    /**
     * @param rawTxHex 0x-prefixed signed raw transaction hex
     * @return an ordered envelope map. Keys: {@code txType}, {@code chainId}
     *         (Long, omitted for pre-EIP-155 legacy), {@code from} (omitted and
     *         replaced by {@code fromError} if recovery fails), {@code to} (null
     *         for contract creation), {@code nonce}, {@code value}, gas fields
     *         ({@code maxFeePerGas}+{@code maxPriorityFeePerGas} for 1559-family,
     *         else {@code gasPrice}), {@code gasLimit}, and {@code data}
     *         (0x-prefixed inner calldata). BigInteger fields are decimal strings.
     * @throws IllegalArgumentException if the hex is empty
     */
    public static Map<String, Object> decode(String rawTxHex) {
        if (rawTxHex == null || rawTxHex.isBlank() || "0x".equalsIgnoreCase(rawTxHex.trim())) {
            throw new IllegalArgumentException("Raw transaction hex is empty.");
        }

        RawTransaction rawTx = TransactionDecoder.decode(rawTxHex.trim());
        ITransaction inner = rawTx.getTransaction();

        Map<String, Object> env = new LinkedHashMap<>();
        env.put("txType", typeLabel(rawTx.getType()));

        Long chainId = extractChainId(rawTx, inner);
        if (chainId != null) {
            env.put("chainId", chainId);
        }

        if (rawTx instanceof SignedRawTransaction) {
            try {
                env.put("from", ((SignedRawTransaction) rawTx).getFrom());
            } catch (Exception e) {
                env.put("fromError", "Sender recovery failed: " + e.getMessage());
            }
        }

        env.put("to", normalizeAddress(rawTx.getTo()));
        env.put("nonce", rawTx.getNonce().toString());
        env.put("value", rawTx.getValue().toString());

        if (inner instanceof Transaction1559) {
            Transaction1559 tx1559 = (Transaction1559) inner;
            env.put("maxPriorityFeePerGas", tx1559.getMaxPriorityFeePerGas().toString());
            env.put("maxFeePerGas", tx1559.getMaxFeePerGas().toString());
        } else {
            env.put("gasPrice", rawTx.getGasPrice().toString());
        }
        env.put("gasLimit", rawTx.getGasLimit().toString());

        env.put("data", normalizeData(rawTx.getData()));
        return env;
    }

    private static Long extractChainId(RawTransaction rawTx, ITransaction inner) {
        if (inner instanceof Transaction2930) {
            // Covers EIP-2930/1559/4844/7702: chain id is an explicit field.
            return ((Transaction2930) inner).getChainId();
        }
        if (rawTx instanceof SignedRawTransaction) {
            // Legacy: derived from EIP-155 `v`; null for pre-EIP-155.
            return ((SignedRawTransaction) rawTx).getChainId();
        }
        return null;
    }

    private static String typeLabel(TransactionType type) {
        switch (type) {
            case EIP1559:
                return "eip1559";
            case EIP2930:
                return "eip2930";
            case EIP4844:
                return "eip4844";
            case EIP7702:
                return "eip7702";
            default:
                return "legacy";
        }
    }

    private static String normalizeAddress(String to) {
        if (to == null || to.isEmpty() || "0x".equalsIgnoreCase(to)) {
            return null; // contract creation
        }
        return to;
    }

    private static String normalizeData(String data) {
        // web3j stores tx data with the 0x prefix stripped (Numeric.cleanHexPrefix);
        // re-add it so the inner calldata is in the form the decoders expect.
        if (data == null || data.isEmpty()) {
            return "0x";
        }
        return data.startsWith("0x") ? data : "0x" + data;
    }
}
