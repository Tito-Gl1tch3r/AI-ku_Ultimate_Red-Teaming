package com.nccgroup.web3decoder.abi;

import com.nccgroup.web3decoder.persistence.CachedAbis;
import burp.api.montoya.MontoyaApi;

public class CachedAbiProvider implements IAbiProvider {

    private final CachedAbis cachedAbis;
    private final int chainId;

    public CachedAbiProvider(MontoyaApi api, int chainId) {
        this.cachedAbis = new CachedAbis(api); // Initialize CachedAbis
        this.chainId = chainId;
    }

    @Override
    public String getAbi(String contractAddress) {
        return cachedAbis.getAbi(chainId, contractAddress);
    }
}
