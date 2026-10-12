package com.nccgroup.web3_decoder.decoder;

import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

/**
 * Regression test for decoding a function output that returns a struct
 * containing a nested struct (tuple-in-tuple). web3j's static-struct decoder
 * derives nested struct sizes via getDeclaredFields()/getConstructors()[0] on
 * our synthetic struct classes, so the generated classes must declare one field
 * per component and expose only the component constructor.
 */
public class NestedStructOutputDecodeTest {

    // CTF.getChallengeInfo -> struct ChallengeInfo { uint256, address, bool, uint256, uint256, Instance{address,bool} }
    private static final String ABI = "[{"
            + "\"type\":\"function\",\"name\":\"getChallengeInfo\","
            + "\"inputs\":[{\"name\":\"_player\",\"type\":\"address\"},{\"name\":\"_levelNumber\",\"type\":\"uint256\"}],"
            + "\"outputs\":[{\"name\":\"info\",\"type\":\"tuple\",\"components\":["
            + "{\"name\":\"levelNumber\",\"type\":\"uint256\"},"
            + "{\"name\":\"factory\",\"type\":\"address\"},"
            + "{\"name\":\"prereqs\",\"type\":\"bool\"},"
            + "{\"name\":\"requiredEther\",\"type\":\"uint256\"},"
            + "{\"name\":\"bounty\",\"type\":\"uint256\"},"
            + "{\"name\":\"instance\",\"type\":\"tuple\",\"components\":["
            + "{\"name\":\"instance\",\"type\":\"address\"},"
            + "{\"name\":\"solved\",\"type\":\"bool\"}"
            + "]}"
            + "]}],\"stateMutability\":\"view\"}]";

    private static final String RETURN_DATA =
            "0x00000000000000000000000000000000000000000000000000000000000000710000000000000000000000004c85be055afc8c5fc73888dba0f4fe807d3b2cf70000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000016345785d8a0000000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000";

    @Test
    public void decodesNestedStructOutput() throws Exception {
        Map<String, Object> decoded = ABIInputDecoder.decodeOutput(ABI, "getChallengeInfo(address,uint256)", RETURN_DATA);

        @SuppressWarnings("unchecked")
        Map<String, Object> output = (Map<String, Object>) decoded.get("output");
        Object info = output.get("info");
        assertInstanceOf(Map.class, info);

        @SuppressWarnings("unchecked")
        Map<String, Object> fields = (Map<String, Object>) info;
        assertEquals(java.math.BigInteger.valueOf(113), fields.get("levelNumber"));
        assertEquals("0x4c85be055afc8c5fc73888dba0f4fe807d3b2cf7", fields.get("factory"));
        assertEquals(false, fields.get("prereqs"));
        assertEquals(new java.math.BigInteger("100000000000000000"), fields.get("requiredEther"));
        assertEquals(java.math.BigInteger.valueOf(10), fields.get("bounty"));

        assertInstanceOf(Map.class, fields.get("instance"));
        @SuppressWarnings("unchecked")
        Map<String, Object> instance = (Map<String, Object>) fields.get("instance");
        assertEquals("0x0000000000000000000000000000000000000000", instance.get("instance"));
        assertEquals(false, instance.get("solved"));
    }
}
