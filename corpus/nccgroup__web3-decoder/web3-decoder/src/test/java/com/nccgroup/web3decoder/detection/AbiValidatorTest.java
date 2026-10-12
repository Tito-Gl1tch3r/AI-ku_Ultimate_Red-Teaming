package com.nccgroup.web3decoder.detection;

import org.junit.jupiter.api.Test;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

class AbiValidatorTest {

    @Test
    void acceptsValidErc20Fragment() {
        String canonical = "[{\"inputs\":[{\"name\":\"owner\",\"type\":\"address\"}]," +
                "\"name\":\"balanceOf\",\"outputs\":[{\"name\":\"\",\"type\":\"uint256\"}]," +
                "\"stateMutability\":\"view\",\"type\":\"function\"}]";
        Optional<DetectedAbi> result = AbiValidator.validate(canonical);
        assertTrue(result.isPresent());
        DetectedAbi abi = result.get();
        assertEquals(1, abi.selectors().size());
        assertEquals("0x70a08231", abi.selectors().get(0));
        // 64 hex chars
        assertEquals(64, abi.fingerprint().length());
    }

    @Test
    void rejectsArrayOfNonObjects() {
        Optional<DetectedAbi> result = AbiValidator.validate("[1,2,3]");
        assertEquals(Optional.empty(), result);
    }

    @Test
    void rejectsObjectMissingTypeField() {
        String json = "[{\"name\":\"foo\",\"inputs\":[],\"outputs\":[]}]";
        Optional<DetectedAbi> result = AbiValidator.validate(json);
        assertEquals(Optional.empty(), result);
    }

    @Test
    void rejectsUnknownType() {
        String json = "[{\"type\":\"nonsense\",\"name\":\"foo\"}]";
        assertEquals(Optional.empty(), AbiValidator.validate(json));
    }

    @Test
    void acceptsEventAndConstructorAlongsideFunction() {
        String json = "[" +
                "{\"type\":\"constructor\",\"inputs\":[],\"stateMutability\":\"nonpayable\"}," +
                "{\"type\":\"event\",\"name\":\"Transfer\",\"inputs\":[],\"anonymous\":false}," +
                "{\"type\":\"function\",\"name\":\"foo\",\"inputs\":[],\"outputs\":[],\"stateMutability\":\"view\"}" +
                "]";
        Optional<DetectedAbi> result = AbiValidator.validate(json);
        assertTrue(result.isPresent());
        // only the function contributes a selector
        assertEquals(1, result.get().selectors().size());
    }

    @Test
    void fingerprintIsStableForSameContent() {
        String json = "[{\"type\":\"function\",\"name\":\"foo\",\"inputs\":[],\"outputs\":[],\"stateMutability\":\"view\"}]";
        String fp1 = AbiValidator.validate(json).get().fingerprint();
        String fp2 = AbiValidator.validate(json).get().fingerprint();
        assertEquals(fp1, fp2);
    }

    @Test
    void fingerprintDiffersForDifferentContent() {
        String a = "[{\"type\":\"function\",\"name\":\"foo\",\"inputs\":[],\"outputs\":[],\"stateMutability\":\"view\"}]";
        String b = "[{\"type\":\"function\",\"name\":\"bar\",\"inputs\":[],\"outputs\":[],\"stateMutability\":\"view\"}]";
        assertNotEquals(AbiValidator.validate(a).get().fingerprint(),
                        AbiValidator.validate(b).get().fingerprint());
    }

    @Test
    void rejectsFunctionWithMalformedTupleInput() {
        // tuple input without "components" -- would make AbiSelectorBuilder throw
        String json = "[{\"type\":\"function\",\"name\":\"foo\","
                + "\"inputs\":[{\"name\":\"x\",\"type\":\"tuple\"}],"
                + "\"outputs\":[],\"stateMutability\":\"view\"}]";
        Optional<DetectedAbi> result = AbiValidator.validate(json);
        assertEquals(Optional.empty(), result);
    }
}
