package com.nccgroup.web3_decoder.annotation;

import com.nccgroup.web3decoder.annotation.Web3RequestSniffer;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class Web3RequestSnifferTest {

    @Test
    void detectsEthCall() {
        assertTrue(Web3RequestSniffer.isCandidate(
                "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"0x1\",\"data\":\"0xabc\"}],\"id\":1}"));
    }

    @Test
    void detectsSendRawTransaction() {
        assertTrue(Web3RequestSniffer.isCandidate(
                "{\"jsonrpc\":\"2.0\",\"method\":\"eth_sendRawTransaction\",\"params\":[\"0x02f8...\"],\"id\":1}"));
    }

    @Test
    void detectsBatch() {
        assertTrue(Web3RequestSniffer.isCandidate(
                "[{\"method\":\"eth_call\",\"id\":1},{\"method\":\"eth_call\",\"id\":2}]"));
    }

    @Test
    void rejectsNonWeb3() {
        assertFalse(Web3RequestSniffer.isCandidate("{\"method\":\"eth_chainId\",\"id\":1}"));
        assertFalse(Web3RequestSniffer.isCandidate("<html>not json</html>"));
        assertFalse(Web3RequestSniffer.isCandidate(""));
        assertFalse(Web3RequestSniffer.isCandidate(null));
    }
}
