package com.codehack.JungleConfig.Core.Adapters;

import com.codehack.JungleConfig.Core.TypeConverterAdapter;
import java.util.UUID;

public class NativeUUIDAdapter implements TypeConverterAdapter {
    @Override
    public String getType() {
        return UUID.class.getSimpleName();
    }

    @Override
    public String ConvertToSave(Object object) {
        return object.toString();
    }

    @Override
    public Object CastToUse(String data) {
        return UUID.fromString(data);
    }
}
